"""Simple character-window chunking for RAG (T-15.03)."""

from __future__ import annotations


def chunk_text(
    text: str,
    *,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[str]:
    """Split ``text`` into overlapping windows (character-based)."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    size = max(64, int(chunk_size))
    ov = max(0, min(int(overlap), size - 1))
    step = max(1, size - ov)
    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + size)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start += step
    return chunks


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / ((na**0.5) * (nb**0.5))
