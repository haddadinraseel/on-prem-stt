from __future__ import annotations

import re

from app.services.summarization.types import OutputLanguage


def is_valid_summary(text: str, output_language: OutputLanguage) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False

    visible_chars = re.sub(r"\s+", "", cleaned)
    if len(visible_chars) < 20:
        return False

    if visible_chars.count("?") / max(len(visible_chars), 1) >= 0.35:
        return False

    if cleaned.lower() in {"summary unavailable", "n/a", "none"}:
        return False

    if output_language == "ar":
        arabic_chars = len(re.findall(r"[\u0600-\u06FF]", cleaned))
        latin_chars = len(re.findall(r"[A-Za-z]", cleaned))
        return arabic_chars >= max(8, latin_chars)

    english_chars = len(re.findall(r"[A-Za-z]", cleaned))
    return english_chars >= 8


def looks_truncated(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return True

    if cleaned.endswith((":", "(", "[", "{", "/", "-", "*", "_", "+")):
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
        "لكن",
        "ثم",
        "أو",
    }
    tokens = re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", cleaned.lower())
    if tokens and tokens[-1] in trailing_words:
        return True

    return cleaned.endswith("**")
