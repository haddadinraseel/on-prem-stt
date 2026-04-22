from __future__ import annotations

import re


def clean_transcript_text(text: str) -> str:
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
