from __future__ import annotations

import logging

import requests

from app.core.config import settings
from app.services.summarization.types import GenerationConfig

logger = logging.getLogger(__name__)


class OllamaBackend:
    backend_name = "ollama"

    def __init__(self) -> None:
        self._session = requests.Session()

    def generate(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        text: str,
        generation: GenerationConfig,
    ) -> str:
        last_error: requests.RequestException | None = None
        for num_predict in generation.max_predict_values:
            payload = {
                "model": model_name,
                "system": system_prompt,
                "prompt": f"{user_prompt}\n\nTranscript:\n{text}\n\nStructured Summary:",
                "stream": False,
                "options": {
                    "temperature": generation.temperature,
                    "top_p": generation.top_p,
                    "num_predict": num_predict,
                },
            }

            response = self._session.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
                timeout=settings.ollama_request_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            output = (data.get("response") or "").strip()
            if output:
                return output

        if last_error:
            raise last_error
        return ""
