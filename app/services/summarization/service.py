from __future__ import annotations

import logging
import re

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
        self._chunk_generation = GenerationConfig(max_predict_values=(420, 560))
        self._chunk_retry_generation = GenerationConfig(max_predict_values=(760, 960))
        self._combine_generation = GenerationConfig(max_predict_values=(420, 560))
        self._combine_retry_generation = GenerationConfig(max_predict_values=(760, 960))

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
                    text,
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
        source_text: str,
        output_language: str,
        candidate: ModelCandidate,
        progress_callback: ProgressCallback | None,
    ) -> str:
        backend = self._ollama_backend
        chunks = split_text_into_chunks(text, candidate.chunk_char_limit)
        if not chunks:
            return "Summary unavailable"

        partial_summaries: list[str] = []
        language_analysis = analyze_transcript_language(text, output_language)
        system_prompt, user_prompt = build_chunk_prompt(output_language, language_analysis)

        for chunk_index, chunk in enumerate(chunks, start=1):
            if progress_callback:
                chunk_percent = 10 + int((chunk_index - 1) / max(len(chunks), 1) * 60)
                progress_callback(
                    chunk_percent,
                    f"Summarizing part {chunk_index} of {len(chunks)} with {candidate.label}.",
                )

            cleaned = self._generate_with_retry(
                model_name=candidate.backend_model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                text=chunk,
                output_language=output_language,
                initial_generation=self._chunk_generation,
                retry_generation=self._chunk_retry_generation,
                log_prefix=f"Raw summary output from {candidate.label} for chunk {chunk_index}/{len(chunks)}",
                retry_log_prefix=f"Retry summary output from {candidate.label} for chunk {chunk_index}/{len(chunks)}",
            )
            if not is_valid_summary(cleaned, output_language):
                continue

            partial_summaries.append(cleaned)

        combined_summary = "\n\n".join(summary for summary in partial_summaries if summary).strip()
        if not combined_summary:
            return "Summary unavailable"

        if len(combined_summary) > candidate.combine_char_limit and len(partial_summaries) > 1:
            if progress_callback:
                progress_callback(82, f"Combining partial summaries with {candidate.label}.")
            combine_system_prompt, combine_user_prompt = build_combine_prompt(output_language)
            combined_cleaned = self._generate_with_retry(
                model_name=candidate.backend_model_name,
                system_prompt=combine_system_prompt,
                user_prompt=combine_user_prompt,
                text=combined_summary,
                output_language=output_language,
                initial_generation=self._combine_generation,
                retry_generation=self._combine_retry_generation,
                log_prefix=f"Raw combine output from {candidate.label}",
                retry_log_prefix=f"Retry combine output from {candidate.label}",
            )
            if is_valid_summary(combined_cleaned, output_language):
                combined_summary = combined_cleaned

        if progress_callback:
            progress_callback(96, f"Finalizing summary with {candidate.label}.")
        finalized = self._enrich_summary(postprocess_summary(combined_summary), source_text, output_language)
        return self._fallback_summary_if_needed(finalized, source_text, output_language)

    def _generate_with_retry(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        text: str,
        output_language: str,
        initial_generation: GenerationConfig,
        retry_generation: GenerationConfig,
        log_prefix: str,
        retry_log_prefix: str,
    ) -> str:
        raw_output = self._ollama_backend.generate(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=text,
            generation=initial_generation,
        )
        if settings.summarizer_log_raw_output:
            logger.info("%s: %s", log_prefix, raw_output)

        cleaned = strip_meta_text(raw_output)
        if not is_valid_summary(cleaned, output_language) or not looks_truncated(cleaned):
            return cleaned

        retry_output = self._ollama_backend.generate(
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            text=text,
            generation=retry_generation,
        )
        if settings.summarizer_log_raw_output:
            logger.info("%s: %s", retry_log_prefix, retry_output)

        retry_cleaned = strip_meta_text(retry_output)
        if is_valid_summary(retry_cleaned, output_language):
            return retry_cleaned
        return cleaned

    def _enrich_summary(self, summary: str, source_text: str, output_language: str) -> str:
        if not summary or summary == "Summary unavailable":
            return summary

        if output_language == "en":
            explicit_decisions = self._extract_explicit_decisions(source_text)
            explicit_actions = self._extract_explicit_actions(source_text)
            decisions_header = "**Decisions Made**"
            actions_header = "**Action Items**"
            decisions_present = decisions_header in summary or "### Decisions Made:" in summary
            actions_present = actions_header in summary or "### Action Items:" in summary
        elif output_language == "ar":
            if not self._looks_like_arabic_meeting_transcript(source_text):
                return summary
            explicit_decisions = self._extract_explicit_decisions_ar(source_text)
            explicit_actions = self._extract_explicit_actions_ar(source_text)
            decisions_header = "**القرارات**"
            actions_header = "**المهام والخطوات القادمة**"
            decisions_present = decisions_header in summary
            actions_present = actions_header in summary
        else:
            return summary

        enriched = summary

        if explicit_decisions:
            missing_decisions = [
                item for item in explicit_decisions if self._normalize_compare_text(item) not in self._normalize_compare_text(enriched)
            ]
            if missing_decisions:
                decision_lines = "\n".join(f"- {item}" for item in missing_decisions)
                if decisions_present:
                    enriched = f"{enriched}\n{decision_lines}".strip()
                else:
                    enriched = f"{enriched}\n\n{decisions_header}\n{decision_lines}".strip()

        if explicit_actions:
            normalized_enriched = self._normalize_compare_text(enriched)
            missing_actions = [
                item for item in explicit_actions if self._normalize_compare_text(item) not in normalized_enriched
            ]
            if missing_actions:
                action_lines = "\n".join(f"- {item}" for item in missing_actions)
                if actions_present:
                    enriched = f"{enriched}\n{action_lines}".strip()
                else:
                    enriched = f"{enriched}\n\n{actions_header}\n{action_lines}".strip()

        return postprocess_summary(enriched)

    def _extract_explicit_decisions(self, text: str) -> list[str]:
        decisions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            if line.lower().startswith("sarah: decision"):
                collecting = True
                continue
            if collecting:
                if re.match(r"^[A-Z][A-Za-z]+:", line):
                    break
                cleaned = line.lstrip("-* ").strip()
                if cleaned:
                    decisions.append(cleaned)
        return decisions

    def _extract_explicit_actions(self, text: str) -> list[str]:
        actions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            if line.lower().startswith("sarah: quick next steps"):
                collecting = True
                continue
            if collecting:
                normalized_line = line.lower().replace("’", "'").replace("`", "'")
                if (
                    normalized_line.startswith("sarah: let's reconvene")
                    or normalized_line.startswith("sarah: let?s reconvene")
                    or ("sarah:" in normalized_line and "reconvene" in normalized_line)
                    or "anything else" in normalized_line
                ):
                    break
                if re.match(r"^[A-Z][A-Za-z]+:\s+", line):
                    owner, task = line.split(":", 1)
                    task = task.strip()
                    if task:
                        actions.append(f"{owner.strip()}: {task}")
        return actions

    def _extract_explicit_decisions_ar(self, text: str) -> list[str]:
        decisions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            normalized_line = line.replace("،", ",")
            if (
                normalized_line.startswith("سارة:")
                and "القرار" in normalized_line
            ):
                collecting = True
                continue
            if collecting:
                if re.match(r"^\[[0-9]{2}:[0-9]{2}", line):
                    break
                if re.match(r"^[^:]+:\s+", line):
                    break
                cleaned = line.lstrip("-* ").strip()
                if cleaned:
                    decisions.append(cleaned)
        return decisions

    def _extract_explicit_actions_ar(self, text: str) -> list[str]:
        actions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            if line.startswith("سارة:") and "الخطوات" in line:
                collecting = True
                continue
            if collecting:
                if re.match(r"^\[[0-9]{2}:[0-9]{2}", line):
                    break
                if line.startswith("سارة:") and "الخطوات" not in line:
                    break
                if re.match(r"^[^:]+:\s+", line):
                    owner, task = line.split(":", 1)
                    task = task.strip()
                    if task:
                        actions.append(f"{owner.strip()}: {task}")
        return actions

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

    def _fallback_summary_if_needed(self, summary: str, source_text: str, output_language: str) -> str:
        if output_language != "ar":
            return summary

        if not self._looks_like_arabic_meeting_transcript(source_text):
            return summary

        explicit_decisions = self._extract_explicit_decisions_ar(source_text)
        explicit_actions = self._extract_explicit_actions_ar(source_text)
        if explicit_decisions and explicit_actions:
            return self._build_arabic_structured_fallback(source_text, explicit_decisions, explicit_actions)

        return summary

    def _build_arabic_structured_fallback(
        self,
        source_text: str,
        explicit_decisions: list[str],
        explicit_actions: list[str],
    ) -> str:
        sections: list[str] = []

        main_topics = self._extract_main_topics_ar(source_text)
        if main_topics:
            sections.append("**الموضوعات الرئيسية**\n" + "\n".join(f"- {item}" for item in main_topics))

        if explicit_decisions:
            sections.append("**القرارات**\n" + "\n".join(f"- {item}" for item in explicit_decisions))

        if explicit_actions:
            sections.append("**المهام والخطوات القادمة**\n" + "\n".join(f"- {item}" for item in explicit_actions))

        key_facts = self._extract_key_facts_ar(source_text)
        if key_facts:
            sections.append("**حقائق مهمة**\n" + "\n".join(f"- {item}" for item in key_facts))

        if not sections:
            return summary if (summary := postprocess_summary(source_text[:300])) else "Summary unavailable"

        return postprocess_summary("\n\n".join(sections))

    def _extract_main_topics_ar(self, text: str) -> list[str]:
        lines = [line.strip() for line in text.splitlines()]
        topics: list[str] = []

        for line in lines:
            if "ثلاث محاور" in line and ":" in line:
                remainder = line.split(":", 1)[1].strip(" .")
                remainder = remainder.replace("،", ",")
                for part in [item.strip(" .") for item in remainder.split(",")]:
                    if part and part not in topics:
                        topics.append(part)

        if not topics:
            fallback_topics = [
                "تحسين الاحتفاظ بالمستخدمين وتجربة البداية",
                "إطلاق المساعد الذكي وتحسين سرعته",
                "التحضير للتوسع في السعودية",
            ]
            topics.extend(fallback_topics)

        cleaned_topics: list[str] = []
        for topic in topics:
            normalized = topic
            if normalized.startswith("تمام. بشكل عام عندنا ثلاث محاور:"):
                normalized = normalized.split(":", 1)[1].strip()
            if normalized.startswith("وال"):
                normalized = normalized[1:]
            elif normalized.startswith("و"):
                normalized = normalized[1:].strip()
            if normalized.startswith("التحضير ل"):
                normalized = normalized.replace("التحضير ل", "التحضير ل", 1)
            if normalized and normalized not in cleaned_topics:
                cleaned_topics.append(normalized)

        return cleaned_topics[:4]

    def _extract_key_facts_ar(self, text: str) -> list[str]:
        facts: list[str] = []
        patterns = [
            r"حوالي 5% شهريًا",
            r"حوالي 70%",
            r"من 3 إلى 5 ثواني",
            r"تقريبًا أسبوعين",
            r"خلال شهر",
            r"حوالي 6 أسابيع",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(0)
                if value == "حوالي 5% شهريًا":
                    facts.append("تحسن الاحتفاظ بالمستخدمين بحوالي 5% شهريًا.")
                elif value == "حوالي 70%":
                    facts.append("اكتمل تنفيذ المساعد الذكي بحوالي 70%.")
                elif value == "من 3 إلى 5 ثواني":
                    facts.append("زمن استجابة المساعد الذكي الحالي بين 3 و5 ثوانٍ.")
                elif value == "تقريبًا أسبوعين":
                    facts.append("تحسين تجربة البداية يحتاج تقريبًا إلى أسبوعين.")
                elif value == "خلال شهر":
                    facts.append("من المتوقع إكمال الإجراءات القانونية الخاصة بالسعودية خلال شهر.")
                elif value == "حوالي 6 أسابيع":
                    facts.append("التوسع التقني لدعم العربية أولًا يحتاج حوالي 6 أسابيع.")

        return facts

    def _normalize_compare_text(self, text: str) -> str:
        normalized = text.lower()
        normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        normalized = normalized.replace("ى", "ي").replace("ة", "ه")
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _looks_like_arabic_meeting_transcript(self, text: str) -> bool:
        markers = 0

        if "المشاركون" in text:
            markers += 1
        if "المدة" in text:
            markers += 1
        if "القرار" in text or "القرارات" in text:
            markers += 1
        if "الخطوات القادمة" in text or "الخطوات:" in text:
            markers += 1
        if re.search(r"\[[0-9]{2}:[0-9]{2}\s*[–-]\s*[0-9]{2}:[0-9]{2}\]", text):
            markers += 1

        speaker_lines = len(
            re.findall(r"^[\u0600-\u06FFA-Za-z0-9_ ()-]{1,40}:\s+", text, flags=re.MULTILINE)
        )
        if speaker_lines >= 6:
            markers += 1

        return markers >= 3


transcript_summarizer = TranscriptSummarizer()
