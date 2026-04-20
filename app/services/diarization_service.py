from __future__ import annotations

from app.models.job import TranscriptSegment


class DiarizationService:
    def diarize(self, segments: list[TranscriptSegment]) -> tuple[str, list[TranscriptSegment]]:
        # Fully local diarization is intentionally disabled by default because robust
        # offline diarization adds heavyweight model dependencies and often requires
        # separate model acquisition steps. The application falls back to timestamped
        # sentence segments so results remain reliable on any local machine.
        return "timestamps_only", segments


diarization_service = DiarizationService()
