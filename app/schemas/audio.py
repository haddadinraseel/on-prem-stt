from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class StartTranscriptionRequest(BaseModel):
    file_id: str = Field(..., description="Stored upload or recording file identifier")
    model_name: str = Field(..., description="Whisper model name")
    source_type: Literal["upload", "recording"] = Field(..., description="upload or recording")
    language: Literal["auto", "ar", "en"] = Field(default="auto", description="Auto or specific language code")


class StoredFileResponse(BaseModel):
    file_id: str
    filename: str
    path: str
    size_bytes: int
    source_type: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    error: str | None = None
    progress: list[dict]
    transcript_text: str | None = None
    summary: str | None = None
    summary_status: str = "not_started"
    summary_error: str | None = None
    summary_progress_percent: int = 0
    summary_progress_message: str | None = None
    segments: list[dict] = Field(default_factory=list)
    text_download_url: str | None = None
    docx_download_url: str | None = None
    diarization_status: str
    device: str | None = None


class ModelStatusResponse(BaseModel):
    name: str
    available_locally: bool
    file_path: str | None = None
