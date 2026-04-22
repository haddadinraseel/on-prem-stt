from __future__ import annotations

import re


def strip_meta_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^structured summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^summary\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^الملخص\s*:\s*", "", cleaned)
    return cleaned.strip(" \n\t\"'")


def postprocess_summary(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned or "Summary unavailable"
