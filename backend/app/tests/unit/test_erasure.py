"""ErasureJobRunner unit tests (T-17.04)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.models.erasure import ErasureJobStatus
from app.models.user import UserStatus
from app.services.erasure_service import ErasureService
from app.workers.erasure_jobs import ErasureJobRunner


@pytest.mark.unit
def test_normalize_scopes_account_implies_documents() -> None:
    scopes = ErasureService._normalize_scopes(["account"])
    assert scopes == ["account", "documents"]


@pytest.mark.unit
def test_normalize_scopes_documents_only() -> None:
    assert ErasureService._normalize_scopes(["documents"]) == ["documents"]


@pytest.mark.unit
def test_runner_deletes_storage_and_anonymizes() -> None:
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    job = MagicMock()
    job.id = job_id
    job.target_user_id = user_id
    job.requested_by_id = user_id
    job.scopes = ["account"]
    job.status = ErasureJobStatus.queued
    job.stats = {}

    doc = MagicMock()
    doc.id = doc_id
    doc.storage_key = "documents/2026/07/x/original.bin"

    target = MagicMock()
    target.id = user_id
    target.status = UserStatus.active

    jobs = MagicMock()
    jobs.get_by_id.return_value = job
    documents = MagicMock()
    documents.list_all_for_owner.return_value = [doc]
    users = MagicMock()
    users.get_by_id.return_value = target
    refresh = MagicMock()
    refresh.revoke_all_for_user.return_value = 2
    storage = MagicMock()
    audit = MagicMock()
    session = MagicMock()

    runner = ErasureJobRunner(
        session,
        storage=storage,
        jobs=jobs,
        documents=documents,
        users=users,
        refresh_tokens=refresh,
        audit=audit,
    )
    result = runner.run(job_id)

    assert result["status"] == ErasureJobStatus.succeeded.value
    storage.delete.assert_called_once_with(doc.storage_key)
    documents.hard_delete.assert_called_once_with(doc)
    users.anonymize_and_deactivate.assert_called_once_with(target)
    refresh.revoke_all_for_user.assert_called_once_with(user_id)
    jobs.mark_succeeded.assert_called_once()
    assert result["stats"]["documents_deleted"] == 1
    assert result["stats"]["account_anonymized"] is True


@pytest.mark.unit
def test_runner_documents_scope_skips_anonymize() -> None:
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job = MagicMock(
        id=job_id,
        target_user_id=user_id,
        requested_by_id=user_id,
        scopes=["documents"],
        status=ErasureJobStatus.queued,
        stats={},
    )
    jobs = MagicMock()
    jobs.get_by_id.return_value = job
    documents = MagicMock()
    documents.list_all_for_owner.return_value = []
    users = MagicMock()
    refresh = MagicMock()

    runner = ErasureJobRunner(
        MagicMock(),
        storage=MagicMock(),
        jobs=jobs,
        documents=documents,
        users=users,
        refresh_tokens=refresh,
        audit=MagicMock(),
    )
    result = runner.run(job_id)
    assert result["status"] == ErasureJobStatus.succeeded.value
    users.anonymize_and_deactivate.assert_not_called()
    refresh.revoke_all_for_user.assert_not_called()
