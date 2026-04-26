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
from app.services.chunking_service import AudioChunk, ChunkingError, chunking_service
from app.services.job_store import job_store
from app.services.merge_service import merge_service
from app.services.model_service import model_service
from app.services.output_service import output_service
from app.services.summarization import transcript_summarizer
from app.services.summarization.service import SummaryCancelledError
from app.services.transliteration_service import transliteration_service

logger = logging.getLogger(__name__)


class JobCancelledError(RuntimeError):
    pass


def _build_transcribe_kwargs(device: str, detected_language: str | None) -> dict[str, object]:
    transcribe_kwargs: dict[str, object] = {
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

    return transcribe_kwargs


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

    def start_summary_job(self, job_id: str) -> None:
        job = job_store.get_job(job_id)
        if not job:
            return

        job.summary_status = "running"
        job.summary_error = None
        job.summary_cancel_requested = False
        job.summary_progress_percent = 1
        job.summary_progress_message = "Preparing transcript for summarization."
        job.add_progress("summarization_requested", "Summary requested. Preparing local summarizer.", 88)
        job_store.update_job(job)

        thread = threading.Thread(target=self._run_summary_job, args=(job_id,), daemon=True)
        thread.start()

    def cancel_job(self, job_id: str) -> JobRecord | None:
        job = job_store.get_job(job_id)
        if not job:
            return None

        job.cancel_requested = True
        job.add_progress("cancelling", "Stopping transcription after the current step finishes.", 100)
        job_store.update_job(job)
        return job

    def cancel_summary_job(self, job_id: str) -> JobRecord | None:
        job = job_store.get_job(job_id)
        if not job:
            return None

        job.summary_cancel_requested = True
        job.summary_status = "cancelling"
        job.summary_progress_message = "Stopping summary after the current request finishes."
        job.add_progress("summary_cancelling", "Stopping summary after the current request finishes.", 100)
        job_store.update_job(job)
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
            job_started_at = time.perf_counter()
            job.status = "running"
            job.cancel_requested = False
            job.add_progress("model_check", "Model check started.", 5)
            job_store.update_job(job)
            logger.info(
                "Job %s started for %s using model '%s' (source_type=%s).",
                job.job_id,
                job.source_path.name,
                job.model_name,
                job.source_type,
            )

            already_downloaded = model_service.is_model_downloaded(job.model_name)
            if not already_downloaded:
                job.add_progress("model_download", "Model download in progress.", 10)
                job_store.update_job(job)
                logger.info("Job %s downloading Whisper model '%s'.", job.job_id, job.model_name)

            model, device, was_cached = model_service.load_model(job.model_name)
            job.device = device
            load_message = "Model loaded from local storage." if was_cached else "Model downloaded and loaded."
            job.add_progress("model_loaded", load_message, 20)
            job_store.update_job(job)
            logger.info(
                "Job %s model ready on %s (cached=%s).",
                job.job_id,
                device,
                was_cached,
            )

            working_dir = settings.temp_dir / job.job_id
            working_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Job %s working directory prepared at %s.", job.job_id, working_dir)

            job.add_progress("audio_normalization", "Audio normalization started.", 28)
            job_store.update_job(job)
            logger.info("Job %s audio normalization started.", job.job_id)
            normalized_path, duration = audio_service.normalize_to_wav(job.source_path, working_dir)
            job.add_progress("audio_normalized", "Audio normalized successfully.", 36)
            job_store.update_job(job)
            logger.info(
                "Job %s audio normalized to %s (duration=%.2fs).",
                job.job_id,
                normalized_path,
                duration,
            )

            detected_language = self._detect_primary_language(model, normalized_path, job.language)
            job.language = detected_language or "auto"
            language_message = (
                f"Using transcription language: {detected_language}."
                if detected_language
                else "No stable Arabic/English detection; using auto mode."
            )
            job.add_progress("language_selected", language_message, 40)
            job_store.update_job(job)
            logger.info("Job %s language selection completed: %s.", job.job_id, job.language)
            self._raise_if_job_cancelled(job)

            job.add_progress("chunking", "Chunking started.", 42)
            job_store.update_job(job)
            logger.info(
                "Job %s chunking started (chunk_length=%ss overlap=%ss).",
                job.job_id,
                settings.chunk_length_seconds,
                settings.chunk_overlap_seconds,
            )
            chunks = chunking_service.create_chunks(normalized_path, duration, working_dir / "chunks")
            job.add_progress("chunking_done", f"Prepared {len(chunks)} audio chunk(s).", 50)
            job_store.update_job(job)
            logger.info("Job %s chunking completed with %s chunk(s).", job.job_id, len(chunks))
            self._raise_if_job_cancelled(job)

            all_segments = self._transcribe_chunks(job, chunks, detected_language, device, model, duration)
            logger.info("Job %s transcription stage produced %s raw segment(s).", job.job_id, len(all_segments))

            job.add_progress("merging", "Merging transcript segments.", 84)
            job_store.update_job(job)
            logger.info("Job %s merging transcript segments.", job.job_id)

            job.segments, job.transcript_text = merge_service.merge_segments(all_segments)
            logger.info(
                "Job %s merge completed with %s final segment(s).",
                job.job_id,
                len(job.segments),
            )

            job.add_progress("outputs", "Generating downloadable files.", 94)
            job_store.update_job(job)
            logger.info("Job %s generating output files.", job.job_id)

            output_dir = settings.outputs_dir / job.job_id
            text_path, docx_path, _metadata_path = output_service.write_outputs(job, output_dir)
            job.text_file = text_path
            job.docx_file = docx_path
            logger.info(
                "Job %s outputs written to %s (txt=%s, docx=%s).",
                job.job_id,
                output_dir,
                text_path.name,
                docx_path.name,
            )

            job.status = "completed"
            job.add_progress("completed", "Transcription completed successfully.", 100)
            job_store.update_job(job)
            logger.info(
                "Job %s completed successfully in %.2fs.",
                job.job_id,
                time.perf_counter() - job_started_at,
            )

        except JobCancelledError:
            logger.info("Transcription job %s cancelled by user.", job_id)
            job.status = "cancelled"
            job.error = "Transcription stopped by user."
            job.add_progress("cancelled", "Transcription stopped.", 100)
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

    def _run_summary_job(self, job_id: str) -> None:
        job = job_store.get_job(job_id)
        if not job:
            return

        try:
            self._generate_summary(job, progress_percent=90)

            if job.text_file or job.docx_file:
                output_dir = settings.outputs_dir / job.job_id
                text_path, docx_path, _metadata_path = output_service.write_outputs(job, output_dir)
                job.text_file = text_path
                job.docx_file = docx_path
                logger.info("Job %s outputs refreshed after summarization.", job.job_id)

            progress_message = (
                "Summary completed successfully."
                if job.summary_status == "completed"
                else "Summary stopped."
                if job.summary_status == "cancelled"
                else "Summary unavailable."
            )
            job.add_progress("summarization_done", progress_message, 100)
            job_store.update_job(job)
        except JobCancelledError:
            logger.info("Summary job %s cancelled by user.", job_id)
            job.summary = None
            job.summary_status = "cancelled"
            job.summary_error = "Summary stopped by user."
            job.summary_progress_percent = 100
            job.summary_progress_message = "Summary stopped."
            job.add_progress("summarization_cancelled", "Summary stopped.", 100)
            job_store.update_job(job)
        except Exception as exc:
            logger.exception("Summary job %s failed", job_id)
            job.summary = "Summary unavailable"
            job.summary_status = "failed"
            job.summary_error = str(exc)
            job.summary_progress_percent = 100
            job.summary_progress_message = "Summary failed."
            job.add_progress("summarization_failed", f"Summary failed: {exc}", 100)
            job_store.update_job(job)

    def _generate_summary(self, job: JobRecord, progress_percent: float) -> None:
        job.summary_status = "running"
        job.summary_error = None
        job.summary_cancel_requested = False
        job.summary_progress_percent = 1
        job.summary_progress_message = "Preparing transcript for summarization."
        job.add_progress("summarization", "Generating local summary.", progress_percent)
        job_store.update_job(job)
        logger.info("Job %s generating local transcript summary.", job.job_id)
        self._raise_if_summary_cancelled(job)

        primary_language = job.language if job.language in {"ar", "en"} else None
        summary = transcript_summarizer.summarize(
            text=job.transcript_text or "",
            language=primary_language,
            progress_callback=lambda percent, message: self._update_summary_progress(job, percent, message),
        )
        self._raise_if_summary_cancelled(job)

        job.summary = summary
        job.summary_status = "completed" if summary and summary != "Summary unavailable" else "failed"
        job.summary_error = None if job.summary_status == "completed" else "Summary unavailable"
        job.summary_progress_percent = 100
        job.summary_progress_message = (
            "Summary completed successfully."
            if job.summary_status == "completed"
            else "Summary unavailable."
        )
        logger.info(
            "Job %s summary generation completed (%s characters, status=%s).",
            job.job_id,
            len(job.summary or ""),
            job.summary_status,
        )

    def _transcribe_chunks(
        self,
        job: JobRecord,
        chunks: list[AudioChunk],
        detected_language: str | None,
        device: str,
        model,
        duration_seconds: float,
    ) -> list[TranscriptSegment]:
        if device == "cpu":
            logger.info(
                "Job %s is using serial CPU transcription for stability with official Whisper.",
                job.job_id,
            )
            job.add_progress(
                "serial_cpu_transcription",
                "Using stable serial transcription on CPU.",
                50,
            )
            job_store.update_job(job)
        elif device == "cuda":
            logger.info(
                "Job %s detected a CUDA-capable GPU and will use GPU acceleration automatically.",
                job.job_id,
            )
            logger.info(
                "Job %s is keeping chunk transcription serial on GPU for stability with official Whisper.",
                job.job_id,
            )
            job.add_progress(
                "gpu_acceleration",
                "CUDA-compatible GPU detected. Using GPU automatically for transcription.",
                50,
            )
            job_store.update_job(job)

        logger.info(
            "Job %s using serial transcription on %s for %s chunk(s).",
            job.job_id,
            device,
            len(chunks),
        )
        return self._transcribe_chunks_serial(job, chunks, detected_language, device, model)

    def _transcribe_chunks_serial(
        self,
        job: JobRecord,
        chunks: list[AudioChunk],
        detected_language: str | None,
        device: str,
        model,
    ) -> list[TranscriptSegment]:
        total_chunks = len(chunks)
        completed_chunks = 0
        chunk_results: list[dict[str, object]] = []
        stage_started_at = time.perf_counter()

        for chunk in chunks:
            self._raise_if_job_cancelled(job)
            final_error: Exception | None = None

            for attempt in range(1, settings.transcription_retries + 1):
                try:
                    self._raise_if_job_cancelled(job)
                    chunk_started_at = time.perf_counter()
                    logger.info(
                        "Job %s processing chunk %s/%s serially (attempt %s, audio %.2fs-%.2fs).",
                        job.job_id,
                        chunk.index,
                        total_chunks,
                        attempt,
                        chunk.start_time,
                        chunk.end_time,
                    )
                    step_name = "transcribing" if attempt == 1 else "retrying_chunk"
                    message = (
                        f"Transcribing chunk {chunk.index} of {total_chunks}."
                        if attempt == 1
                        else f"Retrying failed chunk {chunk.index} of {total_chunks} (attempt {attempt})."
                    )
                    self._update_chunk_progress(job, step_name, message, completed_chunks, total_chunks)

                    result = model.transcribe(str(chunk.path), **_build_transcribe_kwargs(device, detected_language))
                    chunk_results.append(
                        {
                            "chunk_index": chunk.index,
                            "start_time": chunk.start_time,
                            "end_time": chunk.end_time,
                            "segments": result.get("segments", []),
                            "elapsed_seconds": time.perf_counter() - chunk_started_at,
                        }
                    )
                    logger.info(
                        "Job %s finished chunk %s/%s with %s segment(s) in %.2fs.",
                        job.job_id,
                        chunk.index,
                        total_chunks,
                        len(result.get("segments", [])),
                        time.perf_counter() - chunk_started_at,
                    )
                    completed_chunks += 1
                    self._update_chunk_progress(
                        job,
                        "chunk_completed",
                        f"Completed chunk {completed_chunks} of {total_chunks}.",
                        completed_chunks,
                        total_chunks,
                    )
                    final_error = None
                    break
                except Exception as exc:
                    self._raise_if_job_cancelled(job)
                    final_error = exc
                    logger.exception("Chunk %s failed on attempt %s", chunk.index, attempt)
                    time.sleep(min(attempt, 3))

            if final_error is not None:
                raise RuntimeError(
                    f"Chunk {chunk.index} failed after {settings.transcription_retries} attempts."
                ) from final_error

        logger.info(
            "Job %s transcription stage completed serially in %.2fs.",
            job.job_id,
            time.perf_counter() - stage_started_at,
        )
        return self._build_transcript_segments(chunk_results, detected_language)

    def _raise_if_job_cancelled(self, job: JobRecord) -> None:
        if job.cancel_requested:
            raise JobCancelledError("Transcription stopped by user.")

    def _raise_if_summary_cancelled(self, job: JobRecord) -> None:
        if job.summary_cancel_requested:
            raise JobCancelledError("Summary stopped by user.")

    def _update_summary_progress(self, job: JobRecord, percent: int, message: str) -> None:
        if job.summary_cancel_requested:
            raise SummaryCancelledError("Summary stopped by user.")
        job.summary_progress_percent = max(0, min(int(percent), 100))
        job.summary_progress_message = message
        job_store.update_job(job)

    def _build_transcript_segments(
        self,
        chunk_results: list[dict[str, object]],
        detected_language: str | None,
    ) -> list[TranscriptSegment]:
        all_segments: list[TranscriptSegment] = []

        for chunk_result in sorted(chunk_results, key=lambda item: int(item["chunk_index"])):
            start_time = float(chunk_result["start_time"])
            segments = chunk_result.get("segments", [])
            logger.info(
                "Building transcript segments from chunk %s (audio %.2fs-%.2fs) with %s raw segment(s), chunk runtime %.2fs.",
                chunk_result["chunk_index"],
                float(chunk_result.get("start_time", 0.0)),
                float(chunk_result.get("end_time", 0.0)),
                len(segments),
                float(chunk_result.get("elapsed_seconds", 0.0)),
            )

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
                        start=float(segment["start"]) + start_time,
                        end=float(segment["end"]) + start_time,
                        text=text,
                        speaker=None,
                    )
                )

        return all_segments

    def _update_chunk_progress(
        self,
        job: JobRecord,
        step_name: str,
        message: str,
        completed_chunks: int,
        total_chunks: int,
    ) -> None:
        base_progress = 50.0
        progress_span = 30.0
        completion_ratio = completed_chunks / max(total_chunks, 1)
        current_progress = base_progress + completion_ratio * progress_span
        job.add_progress(step_name, message, round(current_progress, 2))
        job_store.update_job(job)

transcription_coordinator = TranscriptionCoordinator()
