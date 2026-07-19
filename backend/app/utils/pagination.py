"""Pagination helpers (SDS ADR — page 1-based, page_size default 20, max 100)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def normalize_page(page: int = 1, page_size: int = 20) -> PageParams:
    p = max(1, page)
    size = min(100, max(1, page_size))
    return PageParams(page=p, page_size=size)
