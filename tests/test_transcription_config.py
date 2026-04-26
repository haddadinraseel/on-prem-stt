from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.schemas.audio import StartTranscriptionRequest
from app.services.transcription_service import _build_transcribe_kwargs


class TranscriptionConfigTests(unittest.TestCase):
    def test_build_transcribe_kwargs_for_arabic(self) -> None:
        kwargs = _build_transcribe_kwargs("cpu", "ar")

        self.assertEqual(kwargs["task"], "transcribe")
        self.assertEqual(kwargs["language"], "ar")
        self.assertEqual(
            kwargs["initial_prompt"],
            "This is primarily Arabic audio and may include some English terms.",
        )
        self.assertFalse(kwargs["fp16"])

    def test_build_transcribe_kwargs_for_english(self) -> None:
        kwargs = _build_transcribe_kwargs("cpu", "en")

        self.assertEqual(kwargs["language"], "en")
        self.assertEqual(
            kwargs["initial_prompt"],
            "This is an English audio transcription.",
        )

    def test_build_transcribe_kwargs_for_auto(self) -> None:
        kwargs = _build_transcribe_kwargs("cuda", None)

        self.assertTrue(kwargs["fp16"])
        self.assertNotIn("language", kwargs)
        self.assertNotIn("initial_prompt", kwargs)

    def test_start_transcription_request_accepts_supported_values(self) -> None:
        payload = StartTranscriptionRequest(
            file_id="upload_123",
            source_type="upload",
            model_name="base",
            language="auto",
        )

        self.assertEqual(payload.source_type, "upload")
        self.assertEqual(payload.language, "auto")

    def test_start_transcription_request_rejects_invalid_source_type(self) -> None:
        with self.assertRaises(ValidationError):
            StartTranscriptionRequest(
                file_id="upload_123",
                source_type="bad",
                model_name="base",
                language="auto",
            )

    def test_start_transcription_request_rejects_invalid_language(self) -> None:
        with self.assertRaises(ValidationError):
            StartTranscriptionRequest(
                file_id="upload_123",
                source_type="upload",
                model_name="base",
                language="fr",
            )


if __name__ == "__main__":
    unittest.main()
