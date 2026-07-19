"""RAG chunking / hash embedding / cosine unit tests (T-15.01 / T-15.03)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock
import uuid

import pytest

from app.adapters.embedding_factory import get_embedding, reset_embedding_cache
from app.adapters.hash_embedding_adapter import HashEmbeddingAdapter
import app.adapters.embedding_factory as embedding_factory
from app.utils.rag_chunking import chunk_text, cosine_similarity


@pytest.mark.unit
def test_chunk_text_overlap() -> None:
    text = "a" * 250
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 3
    assert all(len(c) <= 100 for c in chunks)


@pytest.mark.unit
def test_chunk_text_empty() -> None:
    assert chunk_text("   ") == []


@pytest.mark.unit
def test_cosine_identical() -> None:
    v = [0.5, 0.5, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


@pytest.mark.unit
def test_hash_embedding_stable_and_normalized() -> None:
    adapter = HashEmbeddingAdapter(dimensions=32)
    a = adapter.embed(["hello world"])[0]
    b = adapter.embed(["hello world"])[0]
    assert a == b
    assert len(a) == 32
    norm = sum(x * x for x in a) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-5)
    assert adapter.name == "hash"


@pytest.mark.unit
def test_hash_embedding_differs_by_text() -> None:
    adapter = HashEmbeddingAdapter(dimensions=32)
    a = adapter.embed(["alpha"])[0]
    b = adapter.embed(["beta"])[0]
    assert cosine_similarity(a, b) < 0.99


@pytest.mark.unit
def test_factory_hash(monkeypatch) -> None:
    reset_embedding_cache()
    monkeypatch.setattr(
        embedding_factory,
        "settings",
        SimpleNamespace(embedding_provider="hash", embedding_dimensions=64),
    )
    emb = get_embedding()
    assert isinstance(emb, HashEmbeddingAdapter)
    reset_embedding_cache()


@pytest.mark.unit
def test_rag_retrieve_ranks_relevant_chunk() -> None:
    from app.services.rag_service import RagService

    owner = uuid.uuid4()
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()
    emb = HashEmbeddingAdapter(dimensions=64)
    hi = emb.embed(["invoice total amount due"])[0]
    lo = emb.embed(["completely unrelated weather report"])[0]

    hi_row = MagicMock(
        id=uuid.uuid4(),
        document_id=doc_id,
        ocr_job_id=job_id,
        page=1,
        chunk_index=0,
        text="invoice total amount due",
        embedding=hi,
    )
    lo_row = MagicMock(
        id=uuid.uuid4(),
        document_id=doc_id,
        ocr_job_id=job_id,
        page=2,
        chunk_index=1,
        text="completely unrelated weather report",
        embedding=lo,
    )

    chunks = MagicMock()
    chunks.list_for_owner.return_value = [lo_row, hi_row]
    documents = MagicMock()
    documents.get_by_id.return_value = MagicMock(id=doc_id, owner_id=owner)

    service = RagService(
        MagicMock(),
        chunks=chunks,
        documents=documents,
        embedding=emb,
        cfg=SimpleNamespace(rag_top_k=1, rag_chunk_size=800, rag_chunk_overlap=120),
    )
    actor = MagicMock(id=owner, role="user")
    citations = service.retrieve(
        actor=actor,
        query="what is the invoice total?",
        document_ids=[doc_id],
        top_k=1,
    )
    assert len(citations) == 1
    assert citations[0].chunk_id == hi_row.id
    assert "invoice" in citations[0].snippet.lower()
