"""OpenCV image preprocess adapter (T-4.03 / SDS ADR-011, PRD OCR-03)."""

from __future__ import annotations

import cv2
import numpy as np

from app.adapters.ports import PreprocessOptions


class PreprocessError(ValueError):
    """Raised when input bytes cannot be decoded as an image."""


class OpenCvPreprocessAdapter:
    """Applies optional deskew / denoise / contrast; always returns PNG bytes."""

    def process(
        self,
        image_bytes: bytes,
        options: PreprocessOptions | None = None,
    ) -> bytes:
        opts = options or PreprocessOptions()
        image = self._decode(image_bytes)

        if opts.denoise:
            image = self._denoise(image)
        if opts.contrast:
            image = self._contrast(image)
        if opts.deskew:
            image = self._deskew(image)

        return self._encode_png(image)

    def _decode(self, image_bytes: bytes) -> np.ndarray:
        if not image_bytes:
            raise PreprocessError("empty image bytes")
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise PreprocessError("unable to decode image bytes")
        return image

    def _encode_png(self, image: np.ndarray) -> bytes:
        ok, buf = cv2.imencode(".png", image)
        if not ok:
            raise PreprocessError("unable to encode PNG")
        return buf.tobytes()

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        # Light denoise suitable for document scans (CPU-friendly).
        return cv2.fastNlMeansDenoisingColored(image, None, 6, 6, 7, 21)

    def _contrast(self, image: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_ch = clahe.apply(l_ch)
        merged = cv2.merge([l_ch, a_ch, b_ch])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thresh > 0))
        if coords.size == 0:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        # minAreaRect angle is in [-90, 0); normalize to a small deskew delta.
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.1:
            return image

        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
