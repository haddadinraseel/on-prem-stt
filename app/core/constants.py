from __future__ import annotations

from pathlib import Path


SUPPORTED_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v2",
    "large-v3",
]

SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".webm",
    ".ogg",
    ".aac",
    ".flac",
}

NORMALIZED_AUDIO_SUFFIX = "_normalized.wav"
TRANSCRIPT_TEXT_NAME = "transcript.txt"
TRANSCRIPT_DOCX_NAME = "transcript.docx"
JOB_METADATA_NAME = "result.json"


def is_supported_audio_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
