"""PaddleOcrAdapter unit tests (T-4.04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.paddle_ocr_adapter import OcrEngineError, PaddleOcrAdapter

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_ocr_text.png"


@pytest.fixture(scope="module")
def adapter() -> PaddleOcrAdapter:
    # Module scope: avoid re-downloading / re-loading models per test.
    return PaddleOcrAdapter(default_lang="korean+en")


@pytest.fixture()
def fixture_bytes() -> bytes:
    assert FIXTURE.is_file(), f"missing fixture: {FIXTURE}"
    return FIXTURE.read_bytes()


@pytest.mark.unit
def test_extract_fixture_yields_non_empty_text(
    adapter: PaddleOcrAdapter,
    fixture_bytes: bytes,
) -> None:
    result = adapter.extract(fixture_bytes, lang="korean+en", page=1)
    assert result.page == 1
    assert result.text.strip()
    # Fixture is "HELLO OCR" (may be split into multiple boxes).
    normalized = result.text.upper().replace(" ", "")
    assert "HELLO" in normalized or "OCR" in normalized
    assert isinstance(result.boxes, list)
    assert len(result.boxes) >= 1
    assert result.confidence is not None
    assert 0.0 <= result.confidence <= 1.0
    box = result.boxes[0]
    assert "text" in box and "confidence" in box and "points" in box
    assert len(box["points"]) == 4


@pytest.mark.unit
def test_invalid_bytes_raise(adapter: PaddleOcrAdapter) -> None:
    with pytest.raises(OcrEngineError):
        adapter.extract(b"")
    with pytest.raises(OcrEngineError):
        adapter.extract(b"not-an-image")
