from __future__ import annotations

import logging

from app.core.config import settings
from app.services.summarization.backends import OllamaBackend
from app.services.summarization.chunking import split_text_into_chunks
from app.services.summarization.cleaning import clean_transcript_text
from app.services.summarization.language import analyze_transcript_language
from app.services.summarization.postprocess import postprocess_summary, strip_meta_text
from app.services.summarization.prompts import build_chunk_prompt, build_combine_prompt
from app.services.summarization.types import GenerationConfig, ModelCandidate, ProgressCallback
from app.services.summarization.validation import is_valid_summary, looks_truncated

logger = logging.getLogger(__name__)


class TranscriptSummarizer:
    def __init__(self) -> None:
        self._ollama_backend = OllamaBackend()
        self._chunk_generation = GenerationConfig(max_predict_values=(320, 420))
        self._chunk_retry_generation = GenerationConfig(max_predict_values=(520,))
        self._combine_generation = GenerationConfig(max_predict_values=(260, 360))

    def summarize(self, text: str, language: str | None = None, progress_callback: ProgressCallback | None = None) -> str:
        cleaned_text = clean_transcript_text(text)
        if not cleaned_text:
            return "Summary unavailable"

        preferred_language = language
        if settings.summarizer_language_override in {"ar", "en"}:
            preferred_language = settings.summarizer_language_override

        language_analysis = analyze_transcript_language(cleaned_text, preferred_language)
        candidates = self._build_model_candidates()
        if not candidates:
            return "Summary unavailable"

        for index, candidate in enumerate(candidates, start=1):
            try:
                if progress_callback:
                    progress_callback(
                        3,
                        f"Preparing summary with model {index} of {len(candidates)}: {candidate.label}.",
                    )
                summary = self._summarize_with_candidate(
                    cleaned_text,
                    language_analysis.output_language,
                    candidate,
                    progress_callback,
                )
                if summary and summary != "Summary unavailable":
                    return summary
            except Exception:
                logger.exception("Summarization failed with model %s", candidate.label)
                continue

        return "Summary unavailable"

    def _summarize_with_candidate(
        self,
        text: str,
        output_language: str,
        candidate: ModelCandidate,
        progress_callback: ProgressCallback | None,
    ) -> str:
        backend = self._ollama_backend
        chunks = split_text_into_chunks(text, candidate.chunk_char_limit)
        if not chunks:
            return "Summary unavailable"

        partial_summaries: list[str] = []
        system_prompt, user_prompt = build_chunk_prompt(output_language, analyze_transcript_language(text))

        for chunk_index, chunk in enumerate(chunks, start=1):
            if progress_callback:
                chunk_percent = 10 + int((chunk_index - 1) / max(len(chunks), 1) * 60)
                progress_callback(
                    chunk_percent,
                    f"Summarizing part {chunk_index} of {len(chunks)} with {candidate.label}.",
                )

            raw_output = backend.generate(
                model_name=candidate.backend_model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                text=chunk,
                generation=self._chunk_generation,
            )
            if settings.summarizer_log_raw_output:
                logger.info(
                    "Raw summary output from %s for chunk %s/%s: %s",
                    candidate.label,
                    chunk_index,
                    len(chunks),
                    raw_output,
                )

            cleaned = strip_meta_text(raw_output)
            if not is_valid_summary(cleaned, output_language):
                continue

            if looks_truncated(cleaned):
                retry_output = backend.generate(
                    model_name=candidate.backend_model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    text=chunk,
                    generation=self._chunk_retry_generation,
                )
                if settings.summarizer_log_raw_output:
                    logger.info(
                        "Retry summary output from %s for chunk %s/%s: %s",
                        candidate.label,
                        chunk_index,
                        len(chunks),
                        retry_output,
                    )
                retry_cleaned = strip_meta_text(retry_output)
                if is_valid_summary(retry_cleaned, output_language):
                    cleaned = retry_cleaned

            partial_summaries.append(cleaned)

        combined_summary = "\n\n".join(summary for summary in partial_summaries if summary).strip()
        if not combined_summary:
            return "Summary unavailable"

        if len(combined_summary) > candidate.combine_char_limit and len(partial_summaries) > 1:
            if progress_callback:
                progress_callback(82, f"Combining partial summaries with {candidate.label}.")
            combine_system_prompt, combine_user_prompt = build_combine_prompt(output_language)
            raw_output = backend.generate(
                model_name=candidate.backend_model_name,
                system_prompt=combine_system_prompt,
                user_prompt=combine_user_prompt,
                text=combined_summary,
                generation=self._combine_generation,
            )
            if settings.summarizer_log_raw_output:
                logger.info("Raw combine output from %s: %s", candidate.label, raw_output)
            combined_cleaned = strip_meta_text(raw_output)
            if is_valid_summary(combined_cleaned, output_language):
                combined_summary = combined_cleaned

        if progress_callback:
            progress_callback(96, f"Finalizing summary with {candidate.label}.")
        return postprocess_summary(combined_summary)

    def _build_model_candidates(self) -> list[ModelCandidate]:
        if settings.summarizer_mode == "quality":
            chunk_limit = settings.summarizer_chunk_chars_quality
            combine_limit = settings.summarizer_combine_chars_quality
        else:
            chunk_limit = settings.summarizer_chunk_chars_fast
            combine_limit = settings.summarizer_combine_chars_fast

        names = [settings.summarizer_primary_model] + [
            name.strip() for name in settings.summarizer_fallback_models.split(",") if name.strip()
        ]
        deduped: list[str] = []
        for name in names:
            if name not in deduped:
                deduped.append(name)

        return [
            ModelCandidate(
                label=name,
                backend_model_name=name,
                chunk_char_limit=chunk_limit,
                combine_char_limit=combine_limit,
            )
            for name in deduped
        ]


transcript_summarizer = TranscriptSummarizer()
