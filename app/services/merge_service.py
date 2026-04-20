from __future__ import annotations

from typing import Iterable

from app.models.job import TranscriptSegment


class MergeService:
    def merge_segments(self, segments: Iterable[TranscriptSegment]) -> tuple[list[TranscriptSegment], str]:
        ordered = sorted(segments, key=lambda segment: (segment.start, segment.index))
        merged: list[TranscriptSegment] = []
        previous_text = None

        for segment in ordered:
            cleaned_text = " ".join(segment.text.split())
            if not cleaned_text:
                continue
            if cleaned_text == previous_text:
                continue

            previous_text = cleaned_text
            merged.append(
                TranscriptSegment(
                    index=len(merged) + 1,
                    start=segment.start,
                    end=segment.end,
                    text=cleaned_text,
                    speaker=segment.speaker,
                )
            )

        transcript_text = "\n".join(segment.text for segment in merged)
        return merged, transcript_text


merge_service = MergeService()