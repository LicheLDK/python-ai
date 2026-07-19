"""PDF page helpers for OCR (T-4.07 / SDS OCR_MAX_PAGES, PRD OCR-02)."""

from __future__ import annotations

from typing import Sequence

import fitz  # PyMuPDF


class PdfError(ValueError):
    """Invalid or unreadable PDF bytes."""


def count_pdf_pages(data: bytes) -> int:
    """Return number of pages in a PDF document."""
    if not data:
        raise PdfError("empty PDF bytes")
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            return int(doc.page_count)
    except Exception as exc:  # noqa: BLE001 — normalize library errors
        raise PdfError(f"unable to read PDF: {exc}") from exc


def render_pdf_pages_as_png(
    data: bytes,
    *,
    max_pages: int | None = None,
    scale: float = 2.0,
) -> list[bytes]:
    """Rasterize PDF pages to PNG bytes (1-based page order preserved in list index+1).

    If ``max_pages`` is set, only the first N pages are rendered.
    """
    if not data:
        raise PdfError("empty PDF bytes")
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            total = int(doc.page_count)
            limit = total if max_pages is None else min(total, max(0, max_pages))
            matrix = fitz.Matrix(scale, scale)
            out: list[bytes] = []
            for i in range(limit):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                out.append(pix.tobytes("png"))
            return out
    except PdfError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PdfError(f"unable to render PDF: {exc}") from exc


def is_pdf_mime(mime_type: str) -> bool:
    return mime_type.split(";")[0].strip().lower() == "application/pdf"


def resolve_page_images(
    data: bytes,
    *,
    mime_type: str,
    max_pages: int,
) -> tuple[int, Sequence[bytes]]:
    """Return (total_page_count, png_pages_to_ocr).

    Images → single page. PDFs → split; caller enforces over-limit policy.
    """
    if is_pdf_mime(mime_type):
        total = count_pdf_pages(data)
        pages = render_pdf_pages_as_png(data, max_pages=max_pages)
        return total, pages
    return 1, [data]
