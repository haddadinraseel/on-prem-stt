from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.utils.subprocess_utils import run_command

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    index: int
    path: Path
    start_time: float
    end_time: float


class ChunkingError(Exception):
    """Raised when chunking fails."""


class ChunkingService:
    def create_chunks(self, normalized_audio_path: Path, duration_seconds: float, target_dir: Path) -> list[AudioChunk]:
        target_dir.mkdir(parents=True, exist_ok=True)
        chunk_length = settings.chunk_length_seconds
        overlap = settings.chunk_overlap_seconds

        if duration_seconds <= chunk_length:
            return [
                AudioChunk(
                    index=1,
                    path=normalized_audio_path,
                    start_time=0.0,
                    end_time=duration_seconds,
                )
            ]

        total_chunks = math.ceil(duration_seconds / chunk_length)
        chunks: list[AudioChunk] = []

        for chunk_index in range(total_chunks):
            start = max(0.0, chunk_index * chunk_length - overlap if chunk_index > 0 else 0.0)
            end = min(duration_seconds, (chunk_index + 1) * chunk_length + overlap)
            output_path = target_dir / f"chunk_{chunk_index + 1:04d}.wav"

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(normalized_audio_path),
                "-ss",
                str(start),
                "-to",
                str(end),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
            result = run_command(command)
            if result.returncode != 0:
                logger.error("Chunk creation failed for %s: %s", output_path.name, result.stderr.strip())
                raise ChunkingError(f"Failed to create audio chunk {chunk_index + 1}.")

            chunks.append(
                AudioChunk(
                    index=chunk_index + 1,
                    path=output_path,
                    start_time=float(start),
                    end_time=float(end),
                )
            )

        return chunks


chunking_service = ChunkingService()
