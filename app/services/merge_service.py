from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from app.core.config import settings
from app.models.job import TranscriptSegment


class MergeService:
    def merge_segments(self, segments: Iterable[TranscriptSegment]) -> tuple[list[TranscriptSegment], str]:
        ordered = sorted(segments, key=lambda segment: (segment.start, segment.index))
        merged: list[TranscriptSegment] = []

        for segment in ordered:
            cleaned_text = " ".join(segment.text.split())
            if not cleaned_text:
                continue

            candidate = TranscriptSegment(
                index=len(merged) + 1,
                start=segment.start,
                end=segment.end,
                text=cleaned_text,
                speaker=segment.speaker,
            )

            if merged:
                previous = merged[-1]

                if candidate.text == previous.text and candidate.end <= previous.end:
                    continue

                if self._is_overlap_duplicate(previous, candidate):
                    continue

                if candidate.start < previous.end:
                    candidate.start = previous.end
                    if candidate.start >= candidate.end:
                        continue

            candidate.index = len(merged) + 1
            merged.append(candidate)

        transcript_text = "\n".join(segment.text for segment in merged)
        return merged, transcript_text

    def _is_overlap_duplicate(self, previous: TranscriptSegment, candidate: TranscriptSegment) -> bool:
        overlap_window = max(float(settings.chunk_overlap_seconds), 0.0) + 0.25
        if candidate.start > previous.end + overlap_window:
            return False

        if candidate.end <= previous.end:
            return True

        similarity = SequenceMatcher(None, previous.text, candidate.text).ratio()
        return similarity >= 0.92 and candidate.start <= previous.end + overlap_window


merge_service = MergeService()
