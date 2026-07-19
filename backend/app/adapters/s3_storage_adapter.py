"""S3-compatible StoragePort adapter (T-14.01 / B-P1-S3 / SDS ADR-014).

Works with AWS S3 and MinIO / other S3-compatible endpoints via boto3.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class S3StorageAdapter:
    """Object storage behind the same ``StoragePort`` key layout as local."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        client: BaseClient | None = None,
        endpoint_url: str | None = None,
        region: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        force_path_style: bool | None = None,
    ) -> None:
        self._bucket = bucket or settings.s3_bucket
        if not self._bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3")

        if client is not None:
            self._client = client
            return

        endpoint = (
            endpoint_url
            if endpoint_url is not None
            else (settings.s3_endpoint_url or None)
        )
        region_name = region if region is not None else settings.s3_region
        key_id = (
            access_key_id
            if access_key_id is not None
            else settings.s3_access_key_id
        )
        secret = (
            secret_access_key
            if secret_access_key is not None
            else settings.s3_secret_access_key
        )
        path_style = (
            force_path_style
            if force_path_style is not None
            else settings.s3_force_path_style
        )

        kwargs: dict[str, Any] = {"service_name": "s3", "region_name": region_name}
        if endpoint:
            kwargs["endpoint_url"] = endpoint
        if key_id:
            kwargs["aws_access_key_id"] = key_id
        if secret:
            kwargs["aws_secret_access_key"] = secret
        if path_style:
            kwargs["config"] = Config(s3={"addressing_style": "path"})

        self._client = boto3.client(**kwargs)

    def build_document_key(
        self,
        document_id: uuid.UUID,
        *,
        at: datetime | None = None,
    ) -> str:
        when = at or datetime.now(UTC)
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        else:
            when = when.astimezone(UTC)
        return f"documents/{when:%Y}/{when:%m}/{document_id}/original.bin"

    def put(self, storage_key: str, data: bytes) -> None:
        key = self._normalize_key(storage_key)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def get(self, storage_key: str) -> bytes:
        key = self._normalize_key(storage_key)
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            code = self._error_code(exc)
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise FileNotFoundError(storage_key) from exc
            raise
        body = obj["Body"].read()
        return body if isinstance(body, (bytes, bytearray)) else bytes(body)

    def exists(self, storage_key: str) -> bool:
        key = self._normalize_key(storage_key)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            code = self._error_code(exc)
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            # Some S3-compatible stacks return 404 as HTTPStatusCode only.
            status = (
                exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if getattr(exc, "response", None)
                else None
            )
            if status == 404:
                return False
            raise

    def delete(self, storage_key: str) -> None:
        key = self._normalize_key(storage_key)
        self._client.delete_object(Bucket=self._bucket, Key=key)

    @staticmethod
    def _normalize_key(storage_key: str) -> str:
        key = storage_key.replace("\\", "/").lstrip("/")
        if not key or key.startswith("..") or "/../" in f"/{key}/":
            raise ValueError(f"Invalid storage_key: {storage_key!r}")
        return key

    @staticmethod
    def _error_code(exc: ClientError) -> str:
        error = getattr(exc, "response", None) or {}
        return str((error.get("Error") or {}).get("Code") or "")
