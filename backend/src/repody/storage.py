"""Uploaded documents in S3-compatible object storage (boto3 calls run in a thread)."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Protocol

import boto3
from botocore.exceptions import ClientError

from repody.settings import get_settings


class Store(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...


class S3Store:
    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.s3_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
        )

    async def ensure_bucket(self) -> None:
        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(ensure)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        def get() -> bytes:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(get)


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
