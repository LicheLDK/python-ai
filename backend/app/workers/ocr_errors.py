"""OCR domain errors used by the worker (T-4.07)."""

from __future__ import annotations


class OcrPermanentError(RuntimeError):
    """Non-retryable OCR failure (e.g. page limit exceeded)."""
