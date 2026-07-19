"""Ollama adapter stub (T-5.10) — interface reserved for v1.1."""

from __future__ import annotations

import pytest

from app.adapters.llm_factory import SUPPORTED_PROVIDERS
from app.adapters.ollama_adapter import OllamaAdapter, PROVIDER_NAME
from app.adapters.ports import ChatMessage


def test_ollama_not_in_factory_supported() -> None:
    assert PROVIDER_NAME == "ollama"
    assert "ollama" not in SUPPORTED_PROVIDERS


def test_ollama_stub_raises() -> None:
    adapter = OllamaAdapter()
    assert adapter.name == "ollama"
    assert adapter.health() is False
    with pytest.raises(NotImplementedError):
        adapter.chat([ChatMessage(role="user", content="hi")])
    with pytest.raises(NotImplementedError):
        adapter.vision(images=[b"x"], prompt="p")
