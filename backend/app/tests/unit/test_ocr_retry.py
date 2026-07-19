"""OCR retry backoff helpers (T-4.06)."""

from __future__ import annotations

import pytest

from app.workers.ocr_jobs import compute_ocr_retry_delay_seconds


@pytest.mark.unit
def test_exponential_backoff_until_exhausted() -> None:
    assert compute_ocr_retry_delay_seconds(1, max_attempts=3, base_seconds=2.0) == 2.0
    assert compute_ocr_retry_delay_seconds(2, max_attempts=3, base_seconds=2.0) == 4.0
    assert compute_ocr_retry_delay_seconds(3, max_attempts=3, base_seconds=2.0) is None
    assert compute_ocr_retry_delay_seconds(4, max_attempts=3, base_seconds=2.0) is None
