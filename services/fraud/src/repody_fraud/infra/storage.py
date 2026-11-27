"""S3-compatible object storage adapter for ``repody_fraud``."""

import asyncio
import io
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError

from repody_fraud.settings import get_settings

MISSING_BUCKET = {"404", "NoSuchBucket"}


class S3ArtifactStorage:
    """Thread-safe boto3 S3 wrapper running blocking calls in ``asyncio.to_thread``."""

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
        """Create the bucket if missing."""

        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") not in MISSING_BUCKET:
                    raise
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(_ensure)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.upload_fileobj,
            io.BytesIO(data),
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(_get)


@lru_cache
def get_s3_storage() -> S3ArtifactStorage:
    """Return cached S3 storage adapter."""
    return S3ArtifactStorage()
