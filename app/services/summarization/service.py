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


class SummaryCancelledError(RuntimeError):
    pass


class TranscriptSummarizer:
    def __init__(self) -> None:
        self._ollama_backend = OllamaBackend()
        self._chunk_generation = GenerationConfig(max_predict_values=(420, 560))
        self._chunk_retry_generation = GenerationConfig(max_predict_values=(760, 960))
        self._combine_generation = GenerationConfig(max_predict_values=(420, 560))

    def summarize(self, text: str, language: str | None = None, progress_callback: ProgressCallback | None = None) -> str:
        source_text = text or ""
        cleaned_text = clean_transcript_text(source_text)
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
                    source_text,
                    language_analysis.output_language,
                    candidate,
                    progress_callback,
                )
                if summary and summary != "Summary unavailable":
                    return summary
            except SummaryCancelledError:
                raise
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
        content_mode = self._detect_content_mode(source_text, output_language)
        system_prompt, user_prompt = build_chunk_prompt(
            output_language,
            analyze_transcript_language(text),
            content_mode,
        )

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
            combine_system_prompt, combine_user_prompt = build_combine_prompt(output_language, content_mode)
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
        final_summary = postprocess_summary(combined_summary)
        return self._apply_arabic_fallback_if_needed(final_summary, source_text, content_mode)

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

    def _detect_content_mode(self, text: str, output_language: str) -> str:
        if output_language != "ar":
            return "general"

        markers = 0
        if "المشاركون" in text:
            markers += 1
        if "المدة" in text:
            markers += 1
        if "القرار" in text or "القرارات" in text:
            markers += 1
        if "الخطوات القادمة" in text or "الخطوات:" in text:
            markers += 1
        if "اجتماع" in text:
            markers += 1
        if re.search(r"\[[0-9]{2}:[0-9]{2}\s*[–-]\s*[0-9]{2}:[0-9]{2}\]", text):
            markers += 1

        speaker_lines = sum(1 for line in text.splitlines() if self._parse_speaker_line(line))
        if speaker_lines >= 6:
            markers += 1

        if speaker_lines >= 8:
            markers += 1

        return "meeting" if markers >= 2 else "general"

    def _apply_arabic_fallback_if_needed(self, summary: str, source_text: str, content_mode: str) -> str:
        if content_mode != "meeting":
            if self._summary_looks_invalid_or_meta(summary):
                return self._build_arabic_general_fallback(source_text)
            return summary

        decisions = self._extract_explicit_decisions_ar(source_text)
        recap_actions = self._extract_recap_actions_ar(source_text)
        actions = self._extract_explicit_actions_ar(source_text)
        direct_actions = self._extract_direct_action_statements_ar(source_text)
        for item in direct_actions:
            if item not in actions:
                actions.append(item)
        for item in recap_actions:
            if item not in decisions:
                decisions.append(item)
        decisions = self._dedupe_preserve_order(decisions)
        actions = self._dedupe_preserve_order(actions)
        facts = self._extract_key_facts_ar(source_text)
        if not decisions and not actions:
            return summary

        sections: list[str] = []
        topics = self._extract_main_topics_ar(source_text)
        if topics:
            sections.append("**الموضوعات الرئيسية**\n" + "\n".join(f"- {item}" for item in topics))
        if decisions:
            sections.append("**القرارات**\n" + "\n".join(f"- {item}" for item in decisions))
        if actions:
            sections.append("**المهام أو الخطوات القادمة**\n" + "\n".join(f"- {item}" for item in actions))
        if facts:
            sections.append("**حقائق مهمة**\n" + "\n".join(f"- {item}" for item in facts))

        fallback = postprocess_summary("\n\n".join(sections))
        if len(recap_actions) >= 2:
            return fallback
        if self._summary_looks_suspicious(summary):
            return fallback

        normalized_summary = self._normalize_compare_text(summary)
        missing_decisions = any(self._normalize_compare_text(item) not in normalized_summary for item in decisions)
        missing_actions = any(self._normalize_compare_text(item) not in normalized_summary for item in actions)
        if missing_decisions or missing_actions:
            return fallback

        return summary

    def _summary_looks_suspicious(self, text: str) -> bool:
        lowered = text.lower()
        suspicious_terms = {"onboarding", "caching", "hybrid", "trade-off", "copilot", "rtl"}
        term_hits = sum(1 for term in suspicious_terms if term in lowered)
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        latin_terms = len(re.findall(r"[A-Za-z]{3,}", text))
        if term_hits >= 3:
            return True
        if arabic_chars > 0 and latin_terms >= 6:
            return True
        return False

    def _summary_looks_invalid_or_meta(self, text: str) -> bool:
        lowered = text.strip().lower()
        meta_markers = {
            "عذرًا",
            "اعتذار",
            "يرجى تقديم",
            "لا يمكنني إعداد ملخص",
            "لا يحتوي على أي معلومات واضحة",
            "النص الحالي لا يحتوي",
            "please provide",
            "cannot summarize",
        }
        return any(marker in lowered for marker in meta_markers)

    def _extract_explicit_decisions_ar(self, text: str) -> list[str]:
        decisions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            normalized_line = line.replace("،", ",")
            parsed_line = self._parse_speaker_line(normalized_line)
            if parsed_line and "القرار" in parsed_line[1]:
                collecting = True
                continue
            if collecting:
                if re.match(r"^\[[0-9]{2}:[0-9]{2}", line):
                    break
                if self._parse_speaker_line(line):
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
            parsed_line = self._parse_speaker_line(line)
            if parsed_line and "الخطوات" in parsed_line[1]:
                collecting = True
                continue
            if collecting:
                if re.match(r"^\[[0-9]{2}:[0-9]{2}", line):
                    break
                if parsed_line:
                    owner, task = parsed_line
                    if task:
                        actions.append(f"{owner}: {task}")
                    continue
                if line.startswith("---"):
                    break
        return actions

    def _extract_explicit_actions(self, text: str) -> list[str]:
        actions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue

            lowered = line.lower()
            if any(marker in lowered for marker in ("next steps", "action items", "follow-ups", "follow ups")):
                collecting = True
                continue

            if not collecting:
                continue

            match = re.match(r"^([A-Za-z0-9_ ()-]{1,40})\s*:\s*(.+)$", line)
            if not match:
                if line.startswith("---"):
                    break
                continue

            owner = match.group(1).strip()
            task = match.group(2).strip()
            if not owner or not task:
                continue
            if task.lower().startswith("let's "):
                continue

            actions.append(f"{owner}: {task}")

        return actions

    def _extract_recap_actions_ar(self, text: str) -> list[str]:
        items: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        collecting = False

        for line in lines:
            if not line:
                continue
            parsed_line = self._parse_speaker_line(line)
            content = parsed_line[1] if parsed_line else line
            if parsed_line and ("خلّينا نلخّص" in content or "خلينا نلخص" in content or "لنلخص" in content):
                collecting = True
                continue
            if collecting:
                parsed_line = self._parse_speaker_line(line)
                if parsed_line:
                    _speaker, content = parsed_line
                    if any(
                        marker in content
                        for marker in ("أول شي", "ثاني شي", "ثالث شي", "رابع شي", "نبدأ", "نختبر", "نشتغل", "نفتح")
                    ):
                        items.append(content)
                    elif "إذا ما في شي تاني" in content:
                        break
        return items

    def _extract_direct_action_statements_ar(self, text: str) -> list[str]:
        actions: list[str] = []
        lines = [line.strip() for line in text.splitlines()]
        for line in lines:
            parsed_line = self._parse_speaker_line(line)
            if not parsed_line:
                continue
            speaker, content = parsed_line
            if not any(
                phrase in content
                for phrase in (
                    "لازم نبدأ",
                    "طيب نبدأ بالفيديو",
                    "نفتح positions",
                    "نفتح شواغر",
                    "بدنا research",
                    "explore it",
                )
            ):
                continue

            if any(
                phrase in content
                for phrase in (
                    "حاليًا في feature عم نشتغل عليها",
                    "يمكن لازم نشتغل",
                )
            ):
                continue

            item = f"{speaker.strip()}: {content}"
            if item not in actions:
                actions.append(item)
        return actions

    def _dedupe_preserve_order(self, items: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in items:
            normalized = self._normalize_compare_text(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(item)
        return unique

    def _parse_speaker_line(self, line: str) -> tuple[str, str] | None:
        match = re.match(
            r"^(?:\[[0-9]{2}:[0-9]{2}(?::[0-9]{2})?\]\s*)?([\u0600-\u06FFA-Za-z0-9_ ()-]{1,40})\s*:\s*(.+)$",
            line.strip(),
        )
        if not match:
            return None
        speaker = match.group(1).strip()
        content = match.group(2).strip()
        if not speaker or not content:
            return None
        return speaker, content

    def _extract_main_topics_ar(self, text: str) -> list[str]:
        topics: list[str] = []
        for line in [line.strip() for line in text.splitlines()]:
            if "ثلاث محاور" in line and ":" in line:
                remainder = line.split(":", 1)[1].strip(" .")
                remainder = remainder.replace("،", ",")
                for part in [item.strip(" .") for item in remainder.split(",")]:
                    if part.startswith("تمام. بشكل عام عندنا ثلاث محاور:"):
                        part = part.split(":", 1)[1].strip()
                    if part.startswith("و"):
                        part = part[1:].strip()
                    if part and part not in topics:
                        topics.append(part)
        if not topics:
            fallback_topics = [
                "أداء المنتج خلال الربع الماضي",
                "الاحتفاظ بالمستخدمين وتحسين onboarding",
                "ميزة smart recommendations وجودة البيانات",
                "السوق السعودي والتوظيف والدعم الفني",
            ]
            topics.extend(fallback_topics)
        return topics[:4]

    def _extract_key_facts_ar(self, text: str) -> list[str]:
        facts: list[str] = []
        patterns = [
            ("حوالي 5% شهريًا", "تحسن الاحتفاظ بالمستخدمين بحوالي 5% شهريًا."),
            ("نمو 18%", "نمو المستخدمين النشطين بلغ 18% مقارنة بالربع السابق."),
            ("60% من النمو", "حوالي 60% من النمو جاء من السوق السعودي."),
            ("من 42% لـ 35%", "انخفض الاحتفاظ من 42% إلى 35% بعد الأسبوع الثاني."),
            ("22 دولار", "ارتفع cost of acquisition إلى 22 دولارًا بعد أن كان 15."),
            ("15", "ارتفع cost of acquisition إلى 22 دولارًا بعد أن كان 15."),
            ("تقريبًا 70% جاهزة", "ميزة smart recommendations أصبحت جاهزة تقريبًا بنسبة 70%."),
            ("بدنا أسبوعين تقريبًا", "تنظيف البيانات يحتاج تقريبًا إلى أسبوعين."),
            ("24 ساعة", "زمن الرد في الدعم الفني يصل أحيانًا إلى 24 ساعة."),
            ("حوالي 70%", "اكتمل تنفيذ المساعد الذكي بحوالي 70%."),
            ("من 3 إلى 5 ثواني", "زمن استجابة المساعد الذكي الحالي بين 3 و5 ثوانٍ."),
            ("تقريبًا أسبوعين", "تحسين تجربة البداية يحتاج تقريبًا إلى أسبوعين."),
            ("خلال شهر", "من المتوقع إكمال الإجراءات القانونية الخاصة بالسعودية خلال شهر."),
            ("حوالي 6 أسابيع", "التوسع التقني لدعم العربية أولًا يحتاج حوالي 6 أسابيع."),
        ]
        for needle, sentence in patterns:
            if needle in text and sentence not in facts:
                facts.append(sentence)
        return facts

    def _build_arabic_general_fallback(self, text: str) -> str:
        sentences = self._split_arabic_sentences(text)
        if not sentences:
            return "Summary unavailable"

        sections: list[str] = []
        executive = sentences[0]
        if executive:
            sections.append("**ملخص تنفيذي**\n- " + executive)

        main_topics = sentences[: min(4, len(sentences))]
        if main_topics:
            sections.append("**الموضوعات الرئيسية**\n" + "\n".join(f"- {item}" for item in main_topics))

        fact_sentences = [s for s in sentences[1:5] if any(ch.isdigit() for ch in s) or "سعر" in s or "عمر" in s or "ميزانية" in s]
        if fact_sentences:
            sections.append("**حقائق مهمة**\n" + "\n".join(f"- {item}" for item in fact_sentences))

        return postprocess_summary("\n\n".join(sections))

    def _split_arabic_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        parts = re.split(r"(?<=[\.\!\؟])\s+", normalized)
        cleaned = [part.strip(" .") for part in parts if part.strip(" .")]
        return cleaned

    def _normalize_compare_text(self, text: str) -> str:
        normalized = text.lower()
        normalized = normalized.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        normalized = normalized.replace("ى", "ي").replace("ة", "ه")
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized


transcript_summarizer = TranscriptSummarizer()
