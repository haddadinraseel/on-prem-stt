from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.core.constants import NORMALIZED_AUDIO_SUFFIX, SUPPORTED_EXTENSIONS
from app.utils.subprocess_utils import run_command

logger = logging.getLogger(__name__)


class AudioProcessingError(Exception):
    """Raised when audio normalization fails."""


class AudioService:
    def ensure_supported(self, file_path: Path) -> None:
        if not file_path.exists():
            raise AudioProcessingError("The audio file does not exist.")
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise AudioProcessingError(
                f"Unsupported audio file type '{file_path.suffix}'. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
            )

    def ffmpeg_available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def ffprobe_duration(self, file_path: Path) -> float:
        if shutil.which("ffprobe") is None:
            raise AudioProcessingError("ffprobe is required but was not found. Please install ffmpeg/ffprobe locally.")

        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = run_command(command)
        if result.returncode != 0:
            logger.error("ffprobe failed: %s", result.stderr.strip())
            raise AudioProcessingError("Could not read audio duration. The file may be corrupted.")

        try:
            return float(result.stdout.strip())
        except ValueError as exc:
            raise AudioProcessingError("Could not parse audio duration.") from exc

    def normalize_to_wav(self, source_path: Path, target_dir: Path) -> tuple[Path, float]:
        self.ensure_supported(source_path)
        if not self.ffmpeg_available():
            raise AudioProcessingError("ffmpeg is not installed or not available in PATH.")

        target_dir.mkdir(parents=True, exist_ok=True)
        normalized_path = target_dir / f"{source_path.stem}{NORMALIZED_AUDIO_SUFFIX}"

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(normalized_path),
        ]
        result = run_command(command)
        if result.returncode != 0:
            logger.error("ffmpeg normalization failed: %s", result.stderr.strip())
            raise AudioProcessingError(
                "Audio normalization failed. Please verify the file is valid and ffmpeg is installed correctly."
            )

        duration = self.ffprobe_duration(normalized_path)
        if duration <= 0:
            raise AudioProcessingError("The audio appears to be empty.")

        return normalized_path, duration


audio_service = AudioService()
