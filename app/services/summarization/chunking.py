from __future__ import annotations

import re


def split_into_sentences(text: str) -> list[str]:
    normalized = re.sub(r"([.!?\u061F\u061B])", r"\1<SPLIT>", text)
    return [part.strip() for part in normalized.split("<SPLIT>") if part.strip()]


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    sentences = split_into_sentences(text)
    if not sentences:
        return [text[:max_chars]] if text else []

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(" ".join(current_chunk).strip())
                current_chunk = []
                current_length = 0

            for index in range(0, len(sentence), max_chars):
                piece = sentence[index:index + max_chars].strip()
                if piece:
                    chunks.append(piece)
            continue

        projected_length = current_length + len(sentence) + (1 if current_chunk else 0)
        if current_chunk and projected_length > max_chars:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length = projected_length

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks
