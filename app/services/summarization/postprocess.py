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
    cleaned = re.sub(r"(?m)\n{2,}(?=(?:[-*•]\s))", "\n", cleaned)
    cleaned = re.sub(r"(?m)(\*\*[^*\n]+\*\*|[^:\n]{1,80}:)\n{2,}(?=(?:[-*•]\s))", r"\1\n", cleaned)
    cleaned = re.sub(r"(?m)(?:\n[ \t]*){2,}(?=(?:\*\*[^*\n]+\*\*|[^:\n]{1,80}:)\s*$)", "\n\n", cleaned)
    cleaned = _dedupe_repeated_sections(cleaned)
    return cleaned or "Summary unavailable"


def _dedupe_repeated_sections(text: str) -> str:
    seen_headers: set[str] = set()
    output_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        normalized = stripped.strip(":")
        if normalized in {
            "ملخص تنفيذي",
            "الموضوعات الرئيسية",
            "القرارات",
            "القرارات أو النتائج المهمة",
            "المهام أو الخطوات القادمة",
            "المخاطر أو العوائق",
            "حقائق مهمة",
            "محضر الاجتماع المختصر",
            "Executive Summary",
            "Main Topics",
            "Decisions Made",
            "Decisions / Key Outcomes",
            "Action Items / Next Steps",
            "Blockers / Risks",
            "Key Facts",
            "Meeting Minutes",
        }:
            if normalized in seen_headers:
                continue
            seen_headers.add(normalized)
        output_lines.append(line)
    return "\n".join(output_lines).strip()
