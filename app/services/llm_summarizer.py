from __future__ import annotations

import logging
import re
from threading import Lock
from typing import Callable

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMSummarizer:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session_lock = Lock()
        self._chunk_char_limit = 6500
        self._final_combine_char_limit = 9000

    def summarize_with_llm(
        self,
        text: str,
        language: str | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        cleaned_text = self._clean_transcript_text(text)
        if not cleaned_text:
            return "Summary unavailable"

        prompt_language = self._resolve_prompt_language(language, cleaned_text)
        chunks = self._split_text_into_chunks(cleaned_text, self._chunk_char_limit)
        if not chunks:
            return "Summary unavailable"

        try:
            if progress_callback:
                progress_callback(5, "Preparing transcript for summarization.")

            partial_summaries: list[str] = []
            for index, chunk in enumerate(chunks, start=1):
                if progress_callback:
                    chunk_percent = 10 + int((index - 1) / max(len(chunks), 1) * 65)
                    progress_callback(
                        chunk_percent,
                        f"Summarizing part {index} of {len(chunks)}.",
                    )
                summary = self._generate_summary(
                    chunk,
                    prompt_language,
                    combine_pass=False,
                )
                if summary:
                    partial_summaries.append(summary)

            combined_summary = "\n\n".join(partial_summaries).strip()
            if not combined_summary:
                return "Summary unavailable"

            if len(combined_summary) > self._final_combine_char_limit and len(partial_summaries) > 1:
                if progress_callback:
                    progress_callback(82, "Combining partial summaries.")
                combined_summary = self._generate_summary(
                    combined_summary,
                    prompt_language,
                    combine_pass=True,
                ) or combined_summary

            if progress_callback:
                progress_callback(96, "Finalizing summary.")
            return self._postprocess_summary(combined_summary)
        except requests.RequestException:
            logger.exception("Ollama summarization request failed.")
            return "Summary unavailable"
        except Exception:
            logger.exception("Ollama summarization failed.")
            return "Summary unavailable"

    def _generate_summary(self, text: str, prompt_language: str, combine_pass: bool = False) -> str:
        system_prompt, user_prompt = self._build_prompt(prompt_language, combine_pass)
        predict_values = [260, 360] if not combine_pass else [180, 240]

        for num_predict in predict_values:
            payload = {
                "model": settings.ollama_model,
                "system": system_prompt,
                "prompt": f"{user_prompt}\n\nTranscript:\n{text}\n\nStructured Summary:",
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": num_predict,
                },
            }

            with self._session_lock:
                response = self._session.post(
                    f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                    json=payload,
                    timeout=settings.ollama_request_timeout_seconds,
                )

            response.raise_for_status()
            data = response.json()
            summary = (data.get("response") or "").strip()
            cleaned_summary = self._strip_meta_text(summary)
            if self._looks_invalid_summary(cleaned_summary):
                continue
            if not self._has_enough_source_overlap(cleaned_summary, text):
                continue
            if self._looks_truncated_summary(cleaned_summary) and num_predict != predict_values[-1]:
                continue
            return cleaned_summary

        return ""

    def _build_prompt(self, prompt_language: str, combine_pass: bool) -> tuple[str, str]:
        if prompt_language == "arabic":
            system_prompt = (
                "You summarize noisy Arabic speech-to-text transcripts. "
                "The transcript may contain recognition mistakes, repeated words, broken phrasing, "
                "dialect, and mixed Arabic-English fragments. "
                "First identify the main topics or sections in the transcript. "
                "Then extract the key ideas, decisions, insights, and important supporting details for each topic. "
                "Your job is to infer the intended meaning first, then produce a useful structured summary in Arabic. "
                "The summary must be concise but information-dense. "
                "Do not invent facts. Do not copy long transcript fragments unless necessary. "
                "Output only the final summary."
            )

            if combine_pass:
                system_prompt = (
                    "You are combining several partial summaries created from a noisy Arabic or mixed-language transcript. "
                    "Merge them into one clear, useful, structured Arabic summary. "
                    "Remove repetition, preserve all important insights, ensure logical flow between sections, "
                    "and do not lose key information from earlier summaries. Do not invent facts. "
                    "Output only the final summary."
                )

            user_prompt = (
                "افهم المعنى المقصود أولاً حتى لو كان النص يحتوي على أخطاء تفريغ أو تكرار أو عبارات مكسورة. "
                "ثم اكتب ملخصًا عربيًا منظمًا ومفيدًا يكون أقصر من النص الأصلي لكنه يحتفظ بالمعلومات المهمة. "
                "إذا كان النص يتناول أكثر من فكرة أو موضوع، فقسم الملخص إلى عناوين قصيرة مع نقاط تحت كل عنوان. "
                "استخدم هذا الشكل عند الحاجة:\n"
                "ملخص عام:\n"
                "- ...\n"
                "الموضوعات الرئيسية:\n"
                "[اسم الموضوع]\n"
                "- ...\n"
                "تفاصيل مهمة:\n"
                "- ...\n\n"
                "ركز على الأفكار الأساسية، الحقائق المهمة، الأسماء، التواريخ، النتائج، أو الرسائل الرئيسية عندما تكون موجودة في النص. "
                "ضمّن الأرقام والمقارنات أو المؤشرات المهمة عندما تكون موجودة في النص. "
                "إذا كان النص يحتوي على شرح أو تعليم، فاذكر الإطار أو الخطوات أو العملية التي يتم شرحها مع الأمثلة المهمة والتوصيات أو الاستنتاجات. "
                "تجاهل الحشو والتكرار وعبارات التدريب. "
                "تجنب العبارات العامة أو المبهمة، وكن محددًا فيما تم شرحه أو مناقشته. "
                "لا تخترع معلومات غير موجودة. "
                "اجعل الملخص واضحًا ومفيدًا، وليس قصيرًا جدًا. "
                "أعط الأولوية للأطر والخطوات، والأفكار أو القرارات الرئيسية، والأمثلة المهمة، والخلاصات العملية."
            )

        elif prompt_language == "english":
            system_prompt = (
                "You summarize noisy English speech-to-text transcripts. "
                "The transcript may contain transcription errors, repetition, broken phrasing, and mixed-language fragments. "
                "First identify the main topics or sections in the transcript. "
                "Then extract the key ideas, decisions, insights, and important supporting details for each topic. "
                "Your job is to infer the intended meaning first, then produce a useful structured summary. "
                "The summary must be concise but information-dense. "
                "Do not invent facts. Output only the final summary."
            )

            if combine_pass:
                system_prompt = (
                    "You are combining several partial summaries created from a noisy speech transcript. "
                    "Merge them into one clear, useful, structured summary in English. "
                    "Remove repetition, preserve all important insights, ensure logical flow between sections, "
                    "and do not lose key information from earlier summaries. Do not invent facts. "
                    "Output only the final summary."
                )

            user_prompt = (
                "First understand the intended meaning, even if the transcript contains mistakes, repetition, or broken phrasing. "
                "Then write a structured summary that is shorter than the transcript but still informative. "
                "If the transcript covers multiple topics, organize the summary under short headers with bullet points. "
                "Use a format like this when useful:\n"
                "Overview:\n"
                "- ...\n"
                "Main Points:\n"
                "[Topic Name]\n"
                "- ...\n"
                "Important Details:\n"
                "- ...\n\n"
                "Keep important facts, names, dates, decisions, and main ideas when they appear in the transcript. "
                "Include important numbers, comparisons, or metrics when present. "
                "If the transcript includes explanations or teaching, capture the framework, process, examples, and recommendations or conclusions. "
                "Ignore filler and repetition. "
                "Avoid vague or generic statements. Be specific about what was discussed. "
                "Do not invent facts. "
                "Make the summary useful, not overly short. "
                "Prioritize frameworks or processes, key decisions or insights, important examples, and actionable takeaways."
            )

        else:
            system_prompt = (
                "You summarize noisy multilingual speech-to-text transcripts that may contain Arabic, English, or mixed content. "
                "The transcript may contain recognition mistakes, repetition, broken phrasing, and mixed-language fragments. "
                "First identify the main topics or sections in the transcript. "
                "Then extract the key ideas, decisions, insights, and important supporting details for each topic. "
                "First infer the intended meaning, then produce a useful structured summary in the dominant language of the transcript. "
                "The summary must be concise but information-dense. "
                "Do not invent facts. Output only the final summary."
            )

            if combine_pass:
                system_prompt = (
                    "You are combining several partial summaries created from a noisy multilingual speech transcript. "
                    "Merge them into one clear, useful, structured summary in the dominant language of the transcript. "
                    "Remove repetition, preserve all important insights, ensure logical flow between sections, "
                    "and do not lose key information from earlier summaries. Do not invent facts. "
                    "Output only the final summary."
                )

            user_prompt = (
                "Write a structured summary that is shorter than the transcript but still informative. "
                "If multiple topics are discussed, organize them under short headers with bullet points. "
                "Avoid vague or generic statements and be specific about what was discussed. "
                "Include important numbers, comparisons, or metrics when present. "
                "Keep the most important facts and main ideas. "
                "Ignore filler and repetition. "
                "Do not invent facts. "
                "Prioritize frameworks or processes, key decisions or insights, important examples, and actionable takeaways."
            )

        return system_prompt, user_prompt

    def _resolve_prompt_language(self, language: str | None, text: str) -> str:
        if language == "ar":
            return "arabic"
        if language == "en":
            return "english"

        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        english_chars = len(re.findall(r"[A-Za-z]", text))
        total = arabic_chars + english_chars
        if total == 0:
            return "neutral"
        if arabic_chars / total >= 0.55:
            return "arabic"
        if english_chars / total >= 0.55:
            return "english"
        return "neutral"

    def _clean_transcript_text(self, text: str) -> str:
        cleaned = text or ""
        cleaned = re.sub(
            r"\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\s*-\s*\d{2}:\d{2}:\d{2}(?:\.\d+)?\]\s*",
            " ",
            cleaned,
        )
        cleaned = cleaned.replace("Timestamp:", " ")
        cleaned = cleaned.replace("Speaker:", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _split_text_into_chunks(self, text: str, max_chars: int) -> list[str]:
        sentences = self._split_into_sentences(text)
        if not sentences:
            return [text[:max_chars]]

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(" ".join(current_chunk).strip())
                    current_chunk = []
                    current_length = 0

                for index in range(0, len(sentence), max_chars):
                    piece = sentence[index:index + max_chars].strip()
                    if piece:
                        chunks.append(piece)
                continue

            projected_length = current_length + len(sentence) + (1 if current_chunk else 0)
            if current_chunk and projected_length > max_chars:
                chunks.append(" ".join(current_chunk).strip())
                current_chunk = [sentence]
                current_length = len(sentence)
            else:
                current_chunk.append(sentence)
                current_length = projected_length

        if current_chunk:
            chunks.append(" ".join(current_chunk).strip())

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        normalized = re.sub(r"([.!?\u061F\u061B])", r"\1<SPLIT>", text)
        return [part.strip() for part in normalized.split("<SPLIT>") if part.strip()]

    def _strip_meta_text(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"^structured summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^الملخص\s*:\s*", "", cleaned)
        return cleaned.strip(" \n\t\"'")

    def _postprocess_summary(self, text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned or "Summary unavailable"

    def _looks_invalid_summary(self, text: str) -> bool:
        if not text.strip():
            return True

        visible_chars = re.sub(r"\s+", "", text)
        if not visible_chars:
            return True

        if visible_chars.count("?") / max(len(visible_chars), 1) >= 0.3:
            return True

        if not re.search(r"[\u0600-\u06FFA-Za-z0-9]", text):
            return True

        return False

    def _looks_truncated_summary(self, text: str) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return True

        if cleaned.endswith((":", "(", "[", "{", "/", "-", "*", "_")):
            return True

        trailing_words = {
            "and",
            "or",
            "with",
            "including",
            "because",
            "while",
            "مثل",
            "ومن",
            "و",
            "مع",
            "بما",
        }
        tokens = re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", cleaned.lower())
        if tokens and tokens[-1] in trailing_words:
            return True

        if cleaned.endswith("**"):
            return True

        return False

    def _has_enough_source_overlap(self, summary: str, source_text: str) -> bool:
        source_tokens = set(self._tokenize_for_overlap(source_text))
        summary_tokens = self._tokenize_for_overlap(summary)

        if not source_tokens or not summary_tokens:
            return True

        overlap_count = sum(1 for token in summary_tokens if token in source_tokens)
        overlap_ratio = overlap_count / len(summary_tokens)
        return overlap_ratio >= 0.1 or overlap_count >= 2

    def _tokenize_for_overlap(self, text: str) -> list[str]:
        tokens = re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text.lower())
        return [token for token in tokens if len(token) >= 3]


llm_summarizer = LLMSummarizer()
