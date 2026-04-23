from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class JobProgress:
    step: str
    message: str
    percent: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class TranscriptSegment:
    index: int
    start: float
    end: float
    text: str
    speaker: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
        }


@dataclass
class JobRecord:
    job_id: str
    source_path: Path
    source_type: str
    model_name: str
    language: str = "auto"
    status: str = "queued"
    progress: list[JobProgress] = field(default_factory=list)
    error: str | None = None
    cancel_requested: bool = False
    transcript_text: str | None = None
    summary: str | None = None
    summary_status: str = "not_started"
    summary_error: str | None = None
    summary_cancel_requested: bool = False
    summary_progress_percent: int = 0
    summary_progress_message: str | None = None
    segments: list[TranscriptSegment] = field(default_factory=list)
    text_file: Path | None = None
    docx_file: Path | None = None
    device: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_progress(self, step: str, message: str, percent: float) -> None:
        self.progress.append(JobProgress(step=step, message=message, percent=percent))
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_path": str(self.source_path),
            "source_type": self.source_type,
            "model_name": self.model_name,
            "language": self.language,
            "status": self.status,
            "progress": [vars(item) for item in self.progress],
            "error": self.error,
            "cancel_requested": self.cancel_requested,
            "transcript_text": self.transcript_text,
            "summary": self.summary,
            "summary_status": self.summary_status,
            "summary_error": self.summary_error,
            "summary_cancel_requested": self.summary_cancel_requested,
            "summary_progress_percent": self.summary_progress_percent,
            "summary_progress_message": self.summary_progress_message,
            "segments": [segment.to_dict() for segment in self.segments],
            "text_file": str(self.text_file) if self.text_file else None,
            "docx_file": str(self.docx_file) if self.docx_file else None,
            "device": self.device,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
