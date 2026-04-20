from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path

import whisper

from app.core.config import settings
from app.models.job import JobRecord, TranscriptSegment
from app.services.audio_service import AudioProcessingError, audio_service
from app.services.chunking_service import ChunkingError, chunking_service
from app.services.diarization_service import diarization_service
from app.services.job_store import job_store
from app.services.merge_service import merge_service
from app.services.model_service import model_service
from app.services.output_service import output_service
from app.services.transliteration_service import transliteration_service

logger = logging.getLogger(__name__)


class TranscriptionCoordinator:
    def start_job(self, source_path: Path, source_type: str, model_name: str, language: str = "auto") -> JobRecord:
        job_id = uuid.uuid4().hex
        job = JobRecord(
            job_id=job_id,
            source_path=source_path,
            source_type=source_type,
            model_name=model_name,
            language=language,
        )
        job.add_progress("queued", "Job created and waiting to start.", 0)
        job_store.add_job(job)

        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        return job

    def _detect_primary_language(self, model, normalized_path: Path, requested_language: str) -> str | None:
        if requested_language in {"ar", "en"}:
            logger.info("Using user-requested language override: %s", requested_language)
            return requested_language

        try:
            audio = whisper.load_audio(str(normalized_path))
            audio = whisper.pad_or_trim(audio)
            mel_bins = getattr(model.dims, "n_mels", 80)
            mel = whisper.log_mel_spectrogram(audio, n_mels=mel_bins).to(model.device)

            _, probs = model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            detected_confidence = probs.get(detected_language, 0.0)
            ar_conf = probs.get("ar", 0.0)
            en_conf = probs.get("en", 0.0)

            logger.info(
                "Detected primary language=%s confidence=%.3f (ar=%.3f, en=%.3f)",
                detected_language,
                detected_confidence,
                ar_conf,
                en_conf,
            )

            if detected_language == "ar" and detected_confidence >= 0.60:
                return "ar"
            if detected_language == "en" and detected_confidence >= 0.60:
                return "en"

            logger.info("Language detection not stable enough; falling back to auto mode.")
            return None

        except Exception:
            logger.exception("Language detection failed; falling back to auto.")
            return None

    def _run_job(self, job_id: str) -> None:
        job = job_store.get_job(job_id)
        if not job:
            return

        try:
            job.status = "running"
            job.add_progress("model_check", "Model check started.", 5)
            job_store.update_job(job)

            already_downloaded = model_service.is_model_downloaded(job.model_name)
            if not already_downloaded:
                job.add_progress("model_download", "Model download in progress.", 10)
                job_store.update_job(job)

            model, device, was_cached = model_service.load_model(job.model_name)
            job.device = device
            load_message = "Model loaded from local storage." if was_cached else "Model downloaded and loaded."
            job.add_progress("model_loaded", load_message, 20)
            job_store.update_job(job)

            working_dir = settings.temp_dir / job.job_id
            working_dir.mkdir(parents=True, exist_ok=True)

            job.add_progress("audio_normalization", "Audio normalization started.", 28)
            job_store.update_job(job)
            normalized_path, duration = audio_service.normalize_to_wav(job.source_path, working_dir)
            job.add_progress("audio_normalized", "Audio normalized successfully.", 36)
            job_store.update_job(job)

            detected_language = self._detect_primary_language(model, normalized_path, job.language)
            job.language = detected_language or "auto"
            language_message = (
                f"Using transcription language: {detected_language}."
                if detected_language
                else "No stable Arabic/English detection; using auto mode."
            )
            job.add_progress("language_selected", language_message, 40)
            job_store.update_job(job)

            job.add_progress("chunking", "Chunking started.", 42)
            job_store.update_job(job)
            chunks = chunking_service.create_chunks(normalized_path, duration, working_dir / "chunks")
            job.add_progress("chunking_done", f"Prepared {len(chunks)} audio chunk(s).", 50)
            job_store.update_job(job)

            all_segments: list[TranscriptSegment] = []
            total_chunks = len(chunks)
            base_progress = 50.0
            progress_span = 30.0

            for chunk_position, chunk in enumerate(chunks, start=1):
                final_error: Exception | None = None

                for attempt in range(1, settings.transcription_retries + 1):
                    try:
                        current_progress = base_progress + ((chunk_position - 1) / max(total_chunks, 1)) * progress_span
                        step_name = "transcribing" if attempt == 1 else "retrying_chunk"
                        message = (
                            f"Transcribing chunk {chunk_position} of {total_chunks}."
                            if attempt == 1
                            else f"Retrying failed chunk {chunk_position} of {total_chunks} (attempt {attempt})."
                        )
                        job.add_progress(step_name, message, round(current_progress, 2))
                        job_store.update_job(job)

                        transcribe_kwargs = {
                            "task": "transcribe",
                            "verbose": False,
                            "fp16": (device == "cuda"),
                            "word_timestamps": False,
                            "condition_on_previous_text": False,
                            "temperature": 0.0,
                        }

                        if detected_language in {"ar", "en"}:
                            transcribe_kwargs["language"] = detected_language

                        if detected_language == "ar":
                            transcribe_kwargs["initial_prompt"] = "This is primarily Arabic audio and may include some English terms."
                        elif detected_language == "en":
                            transcribe_kwargs["initial_prompt"] = "This is an English audio transcription."

                        result = model.transcribe(str(chunk.path), **transcribe_kwargs)

                        segments = result.get("segments", [])
                        for segment in segments:
                            text = str(segment.get("text", "")).strip()
                            if not text:
                                continue

                            text = transliteration_service.transform_text_if_arabic_context(
                                text=text,
                                primary_language=detected_language,
                            )

                            all_segments.append(
                                TranscriptSegment(
                                    index=len(all_segments) + 1,
                                    start=float(segment["start"]) + chunk.start_time,
                                    end=float(segment["end"]) + chunk.start_time,
                                    text=text,
                                    speaker=None,
                                )
                            )

                        final_error = None
                        break

                    except Exception as exc:
                        final_error = exc
                        logger.exception("Chunk %s failed on attempt %s", chunk.index, attempt)
                        time.sleep(min(attempt, 3))

                if final_error is not None:
                    raise RuntimeError(
                        f"Chunk {chunk.index} failed after {settings.transcription_retries} attempts."
                    ) from final_error

            job.add_progress("merging", "Merging transcript segments.", 84)
            job_store.update_job(job)

            diarization_status, diarized_segments = diarization_service.diarize(all_segments)
            job.diarization_status = diarization_status
            job.segments, job.transcript_text = merge_service.merge_segments(diarized_segments)

            job.add_progress("outputs", "Generating downloadable files.", 92)
            job_store.update_job(job)

            output_dir = settings.outputs_dir / job.job_id
            text_path, docx_path, _metadata_path = output_service.write_outputs(job, output_dir)
            job.text_file = text_path
            job.docx_file = docx_path

            job.status = "completed"
            job.add_progress("completed", "Transcription completed successfully.", 100)
            job_store.update_job(job)

        except (AudioProcessingError, ChunkingError, ValueError, RuntimeError) as exc:
            logger.exception("Transcription job %s failed", job_id)
            job.status = "failed"
            job.error = str(exc)
            job.add_progress("failed", f"Job failed: {exc}", 100)
            job_store.update_job(job)
        except Exception as exc:
            logger.exception("Unexpected failure in job %s", job_id)
            job.status = "failed"
            job.error = "An unexpected error occurred during transcription."
            job.add_progress("failed", f"Job failed: {exc}", 100)
            job_store.update_job(job)


transcription_coordinator = TranscriptionCoordinator()
