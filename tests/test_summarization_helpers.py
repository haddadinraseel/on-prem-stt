from __future__ import annotations

import unittest

from app.services.summarization.service import TranscriptSummarizer
from app.services.summarization.postprocess import postprocess_summary, strip_meta_text
from app.services.summarization.prompts import build_chunk_prompt, build_combine_prompt
from app.services.summarization.types import LanguageAnalysis
from app.services.summarization.validation import looks_truncated


class SummarizationHelpersTests(unittest.TestCase):
    def test_arabic_chunk_prompt_contains_readable_arabic(self) -> None:
        analysis = LanguageAnalysis("arabic", "ar", arabic_chars=120, english_chars=10)
        _system_prompt, user_prompt = build_chunk_prompt("ar", analysis)

        self.assertIn("تعامل مع النص", user_prompt)
        self.assertNotIn("Ø", user_prompt)

    def test_arabic_combine_prompt_contains_readable_arabic(self) -> None:
        _system_prompt, user_prompt = build_combine_prompt("ar")

        self.assertIn("ادمج الملخصات الجزئية", user_prompt)
        self.assertNotIn("Ø", user_prompt)

    def test_strip_meta_text_removes_arabic_summary_prefix(self) -> None:
        self.assertEqual(strip_meta_text("الملخص: تفاصيل مهمة"), "تفاصيل مهمة")

    def test_looks_truncated_detects_arabic_trailing_word(self) -> None:
        self.assertTrue(looks_truncated("هذه نقاط مهمة مع"))

    def test_looks_truncated_detects_incomplete_numbered_list(self) -> None:
        self.assertTrue(looks_truncated("Proposed Solutions:\n1."))

    def test_postprocess_summary_keeps_spacing_stable(self) -> None:
        self.assertEqual(postprocess_summary("سطر أول\n\n\nسطر ثان"), "سطر أول\n\nسطر ثان")

    def test_extract_explicit_actions_from_transcript(self) -> None:
        summarizer = TranscriptSummarizer()
        transcript = """
Sarah: Quick next steps:
Omar: finalize AI feature scope by end of week
Lina: address latency + onboarding fixes
Sarah: Let's reconvene next week with updates.
"""
        self.assertEqual(
            summarizer._extract_explicit_actions(transcript),
            [
                "Omar: finalize AI feature scope by end of week",
                "Lina: address latency + onboarding fixes",
            ],
        )


if __name__ == "__main__":
    unittest.main()
