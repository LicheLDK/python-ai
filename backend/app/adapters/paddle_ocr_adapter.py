"""PaddleOCR engine adapter (T-4.04 / SDS ADR-011).

Product lang tag ``korean+en`` maps to PaddleOCR ``korean``
(korean_PP-OCRv4_rec covers Korean + English).
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.adapters.ports import OcrPageResult
from app.core.config import settings

# Product / API lang → PaddleOCR lang code
_LANG_MAP: dict[str, str] = {
    "korean+en": "korean",
    "ko+en": "korean",
    "korean": "korean",
    "ko": "korean",
    "en": "en",
    "english": "en",
}


class OcrEngineError(ValueError):
    """Raised when image bytes cannot be OCR'd."""


class PaddleOcrAdapter:
    """CPU PaddleOCR wrapper returning SDS-shaped page results."""

    def __init__(
        self,
        *,
        default_lang: str | None = None,
        use_angle_cls: bool = True,
        use_gpu: bool = False,
    ) -> None:
        self._default_lang = default_lang or settings.ocr_lang
        self._use_angle_cls = use_angle_cls
        self._use_gpu = use_gpu
        # Any: keep import path free of paddleocr for CI (T-11.01).
        self._engines: dict[str, Any] = {}

    def extract(
        self,
        image_bytes: bytes,
        *,
        lang: str | None = None,
        page: int = 1,
    ) -> OcrPageResult:
        image = self._decode(image_bytes)
        engine = self._get_engine(lang or self._default_lang)
        raw = engine.ocr(image, cls=self._use_angle_cls)
        return self._normalize(raw, page=page)

    def _resolve_lang(self, lang: str) -> str:
        key = lang.strip().lower()
        if key in _LANG_MAP:
            return _LANG_MAP[key]
        # Allow passthrough of native paddle codes (e.g. "ch", "japan").
        return key

    def _get_engine(self, lang: str) -> Any:
        paddle_lang = self._resolve_lang(lang)
        if paddle_lang not in self._engines:
            # Lazy import so FastAPI/tests can load without Paddle in CI.
            from paddleocr import PaddleOCR

            self._engines[paddle_lang] = PaddleOCR(
                use_angle_cls=self._use_angle_cls,
                lang=paddle_lang,
                use_gpu=self._use_gpu,
                show_log=False,
            )
        return self._engines[paddle_lang]

    def _decode(self, image_bytes: bytes) -> np.ndarray:
        if not image_bytes:
            raise OcrEngineError("empty image bytes")
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise OcrEngineError("unable to decode image bytes")
        return image

    def _normalize(self, raw: Any, *, page: int) -> OcrPageResult:
        # PaddleOCR 2.x: [ [ [box, (text, score)], ... ] ] or [None]
        lines: list[Any] = []
        if raw is None:
            lines = []
        elif isinstance(raw, list) and raw and isinstance(raw[0], list):
            # Single-image call → one page list (may be None)
            page_lines = raw[0]
            lines = page_lines if page_lines else []
        elif isinstance(raw, list):
            lines = raw
        else:
            lines = []

        boxes: list[dict[str, Any]] = []
        texts: list[str] = []
        scores: list[float] = []

        for item in lines:
            if not item or len(item) < 2:
                continue
            points_raw, rec = item[0], item[1]
            if not isinstance(rec, (list, tuple)) or len(rec) < 2:
                continue
            text = str(rec[0]).strip()
            try:
                conf = float(rec[1])
            except (TypeError, ValueError):
                conf = 0.0
            points = [[float(p[0]), float(p[1])] for p in points_raw]
            if text:
                texts.append(text)
                scores.append(conf)
                boxes.append(
                    {
                        "text": text,
                        "confidence": round(conf, 4),
                        "points": points,
                    }
                )

        joined = " ".join(texts).strip()
        avg_conf: float | None = None
        if scores:
            avg_conf = round(sum(scores) / len(scores), 4)

        return OcrPageResult(
            page=page,
            text=joined,
            boxes=boxes,
            confidence=avg_conf,
        )
