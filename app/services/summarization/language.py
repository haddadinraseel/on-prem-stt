from __future__ import annotations

import re

from app.services.summarization.types import LanguageAnalysis


def analyze_transcript_language(text: str, preferred_language: str | None = None) -> LanguageAnalysis:
    if preferred_language == "ar":
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        english_chars = len(re.findall(r"[A-Za-z]", text))
        return LanguageAnalysis("arabic", "ar", arabic_chars, english_chars)

    if preferred_language == "en":
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
        english_chars = len(re.findall(r"[A-Za-z]", text))
        return LanguageAnalysis("english", "en", arabic_chars, english_chars)

    arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
    english_chars = len(re.findall(r"[A-Za-z]", text))
    total = arabic_chars + english_chars

    if total == 0:
        return LanguageAnalysis("neutral", "en", arabic_chars, english_chars)

    arabic_ratio = arabic_chars / total
    english_ratio = english_chars / total

    if arabic_ratio >= 0.58:
        return LanguageAnalysis("arabic", "ar", arabic_chars, english_chars)
    if english_ratio >= 0.58:
        return LanguageAnalysis("english", "en", arabic_chars, english_chars)

    output_language = "ar" if arabic_chars >= english_chars else "en"
    return LanguageAnalysis("mixed", output_language, arabic_chars, english_chars)
