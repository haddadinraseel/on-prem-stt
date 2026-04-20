from __future__ import annotations

import logging
from pathlib import Path

import whisper

from app.core.config import settings
from app.core.constants import SUPPORTED_MODELS
from app.services.device_service import detect_torch_device

logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], whisper.Whisper] = {}

    def list_models(self) -> list[dict[str, str | bool | None]]:
        models: list[dict[str, str | bool | None]] = []
        for model_name in SUPPORTED_MODELS:
            model_path = self.get_model_path(model_name)
            available = bool(model_path and model_path.exists())
            models.append(
                {
                    "name": model_name,
                    "available_locally": available,
                    "file_path": str(model_path) if available else None,
                }
            )
        return models

    def get_model_path(self, model_name: str) -> Path | None:
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        if model_name not in whisper._MODELS:
            return None

        filename = Path(whisper._MODELS[model_name]).name
        candidate = settings.models_dir / filename
        return candidate

    def is_model_downloaded(self, model_name: str) -> bool:
        model_path = self.get_model_path(model_name)
        return bool(model_path and model_path.exists())

    def load_model(self, model_name: str) -> tuple[whisper.Whisper, str, bool]:
        if model_name not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_name}")

        device = detect_torch_device()
        cache_key = (model_name, device)
        already_downloaded = self.is_model_downloaded(model_name)

        if cache_key in self._cache:
            return self._cache[cache_key], device, already_downloaded

        logger.info("Loading Whisper model '%s' on %s", model_name, device)
        model = whisper.load_model(model_name, device=device, download_root=str(settings.models_dir))
        self._cache[cache_key] = model
        return model, device, already_downloaded


model_service = ModelService()