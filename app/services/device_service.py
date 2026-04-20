from __future__ import annotations

import logging

import torch

logger = logging.getLogger(__name__)


def detect_torch_device() -> str:
    if torch.cuda.is_available():
        try:
            device_name = torch.cuda.get_device_name(0)
            logger.info("Using CUDA device: %s", device_name)
            return "cuda"
        except Exception:
            logger.exception("CUDA reported available but device lookup failed. Falling back to CPU.")
    return "cpu"
