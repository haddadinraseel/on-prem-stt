from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Protocol


DetectedLanguage = Literal["arabic", "english", "mixed", "neutral"]
OutputLanguage = Literal["ar", "en"]
ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class LanguageAnalysis:
    detected_language: DetectedLanguage
    output_language: OutputLanguage
    arabic_chars: int
    english_chars: int


@dataclass(frozen=True)
class ModelCandidate:
    label: str
    backend_model_name: str
    chunk_char_limit: int
    combine_char_limit: int


@dataclass(frozen=True)
class GenerationConfig:
    max_predict_values: tuple[int, ...]
    temperature: float = 0.1
    top_p: float = 0.9


class SummarizationBackend(Protocol):
    backend_name: str

    def generate(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_prompt: str,
        text: str,
        generation: GenerationConfig,
    ) -> str:
        ...
