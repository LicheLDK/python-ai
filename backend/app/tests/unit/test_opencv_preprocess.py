"""OpenCvPreprocessAdapter unit tests (T-4.03)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.adapters.opencv_preprocess_adapter import (
    OpenCvPreprocessAdapter,
    PreprocessError,
)
from app.adapters.ports import PreprocessOptions

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_preprocess.png"


@pytest.fixture()
def adapter() -> OpenCvPreprocessAdapter:
    return OpenCvPreprocessAdapter()


@pytest.fixture()
def fixture_bytes() -> bytes:
    assert FIXTURE.is_file(), f"missing fixture: {FIXTURE}"
    return FIXTURE.read_bytes()


def _decode(png_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    assert image is not None
    return image


@pytest.mark.unit
def test_process_fixture_all_options(adapter: OpenCvPreprocessAdapter, fixture_bytes: bytes) -> None:
    out = adapter.process(
        fixture_bytes,
        PreprocessOptions(deskew=True, denoise=True, contrast=True),
    )
    assert out.startswith(b"\x89PNG")
    image = _decode(out)
    assert image.ndim == 3
    assert image.shape[0] > 0 and image.shape[1] > 0
    # Pipeline must change pixels vs raw decode of the skewed/noisy fixture.
    original = _decode(fixture_bytes)
    assert image.shape == original.shape
    assert not np.array_equal(image, original)


@pytest.mark.unit
def test_process_noop_options_still_png(adapter: OpenCvPreprocessAdapter, fixture_bytes: bytes) -> None:
    out = adapter.process(fixture_bytes, PreprocessOptions())
    assert out.startswith(b"\x89PNG")
    _decode(out)


@pytest.mark.unit
def test_process_each_flag_independently(
    adapter: OpenCvPreprocessAdapter,
    fixture_bytes: bytes,
) -> None:
    for opts in (
        PreprocessOptions(deskew=True),
        PreprocessOptions(denoise=True),
        PreprocessOptions(contrast=True),
    ):
        out = adapter.process(fixture_bytes, opts)
        assert out.startswith(b"\x89PNG")
        _decode(out)


@pytest.mark.unit
def test_invalid_bytes_raise(adapter: OpenCvPreprocessAdapter) -> None:
    with pytest.raises(PreprocessError):
        adapter.process(b"not-an-image")
    with pytest.raises(PreprocessError):
        adapter.process(b"")
