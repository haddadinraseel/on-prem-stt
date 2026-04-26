from __future__ import annotations

import unittest
from unittest.mock import Mock

import requests

from app.services.summarization.backends import OllamaBackend
from app.services.summarization.types import GenerationConfig


class OllamaBackendTests(unittest.TestCase):
    def test_generate_retries_until_successful_response(self) -> None:
        backend = OllamaBackend()
        failed_response = requests.ConnectionError("offline")
        success_response = Mock()
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = {"response": "final summary"}

        backend._session = Mock()
        backend._session.post.side_effect = [failed_response, success_response]

        result = backend.generate(
            model_name="qwen2.5:3b",
            system_prompt="system",
            user_prompt="user",
            text="transcript",
            generation=GenerationConfig(max_predict_values=(32, 64)),
        )

        self.assertEqual(result, "final summary")
        self.assertEqual(backend._session.post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
