from __future__ import annotations
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "On-Prem STT"
    app_version: str = "1.0.0"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    models_dir: Path | None = None
    outputs_dir: Path | None = None
    recordings_dir: Path | None = None
    uploads_dir: Path | None = None
    temp_dir: Path | None = None
    logs_dir: Path | None = None

    max_audio_duration_hours: int = 4
    chunk_length_seconds: int = 180
    chunk_overlap_seconds: int = 2
    transcription_retries: int = 3
    whisper_default_language: str = "ar"
    poll_interval_seconds: float = 2.0
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_request_timeout_seconds: int = 300

    summarizer_mode: Literal["fast", "quality"] = "fast"
    summarizer_language_override: Literal["auto", "ar", "en"] = "auto"
    summarizer_primary_model: str = "qwen2.5:3b"
    summarizer_fallback_models: str = ""
    summarizer_chunk_chars_fast: int = 4200
    summarizer_chunk_chars_quality: int = 5600
    summarizer_combine_chars_fast: int = 6400
    summarizer_combine_chars_quality: int = 9000
    summarizer_log_raw_output: bool = True

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    def model_post_init(self, __context: object) -> None:
        self.models_dir = self.models_dir or self.project_root / "models"
        self.outputs_dir = self.outputs_dir or self.project_root / "outputs"
        self.recordings_dir = self.recordings_dir or self.project_root / "recordings"
        self.uploads_dir = self.uploads_dir or self.project_root / "temp" / "uploads"
        self.temp_dir = self.temp_dir or self.project_root / "temp"
        self.logs_dir = self.logs_dir or self.project_root / "logs"

        for directory in (
            self.models_dir,
            self.outputs_dir,
            self.recordings_dir,
            self.uploads_dir,
            self.temp_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
