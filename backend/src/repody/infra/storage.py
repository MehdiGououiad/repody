"""Uploaded documents in S3-compatible object storage (boto3 calls run in a thread; boto3
clients are thread-safe).

Uploads stream from the request's spooled file (``upload_fileobj``: multipart for large
files), so a run's files are never all held in memory.
"""

import asyncio
from functools import lru_cache
from typing import Any, BinaryIO, Protocol

import boto3
import structlog
from botocore.exceptions import ClientError

from repody.settings import get_settings

log = structlog.get_logger(__name__)

# S3 DeleteObjects takes at most 1000 keys per request.
DELETE_BATCH = 1000
MISSING_BUCKET = {"404", "NoSuchBucket"}


class Store(Protocol):
    async def put(self, key: str, file: BinaryIO, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, keys: list[str]) -> None: ...


class S3Store:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        )

    async def ensure_bucket(self) -> None:
        """Create the bucket when it does not exist (any other error is raised)."""

        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") not in MISSING_BUCKET:
                    raise
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(ensure)

    async def put(self, key: str, file: BinaryIO, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.upload_fileobj,
            file,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    async def get(self, key: str) -> bytes:
        def get() -> bytes:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(get)

    async def delete(self, keys: list[str]) -> None:
        """Delete objects (missing ones count as deleted); keys S3 could not delete are logged."""

        def delete() -> None:
            for start in range(0, len(keys), DELETE_BATCH):
                batch = [{"Key": key} for key in keys[start : start + DELETE_BATCH]]
                response = self._client.delete_objects(
                    Bucket=self._bucket, Delete={"Objects": batch, "Quiet": True}
                )
                if errors := response.get("Errors"):
                    log.error(
                        "storage_delete_failed",
                        keys=[e.get("Key") for e in errors],
                        codes=sorted({e.get("Code") for e in errors}),
                    )

        if keys:
            await asyncio.to_thread(delete)


_override: Store | None = None


@lru_cache
def _s3() -> S3Store:
    return S3Store()


def get_store() -> Store:
    return _override or _s3()


def use_store(store: Store | None) -> None:
    """Swap the store (tests use an in-memory one; None restores S3)."""
    global _override
    _override = store
