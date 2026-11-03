"""S3/MinIO object store (boto3 calls run in a worker thread)."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from repody.infra.storage.base import PresignedPut
from repody.settings import Settings


def _make_client(endpoint_url: str, settings: Settings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _endpoint(settings: Settings) -> str:
    # In-cluster MinIO listens on HTTP; TLS for browser uploads is at the edge (Caddy).
    return f"http://{settings.minio_endpoint}"


def _public_endpoint(settings: Settings) -> str:
    if settings.minio_public_endpoint:
        raw = settings.minio_public_endpoint.strip()
        if raw.startswith(("http://", "https://")):
            return raw.rstrip("/")
        scheme = "https" if settings.minio_secure else "http"
        return f"{scheme}://{raw.rstrip('/')}"
    return _endpoint(settings)


def build_s3_clients(settings: Settings) -> tuple[Any, Any]:
    """Return (internal_client, presign_client)."""
    internal_endpoint = _endpoint(settings)
    public_endpoint = _public_endpoint(settings)
    internal = _make_client(internal_endpoint, settings)
    if internal_endpoint == public_endpoint:
        return internal, internal
    return internal, _make_client(public_endpoint, settings)


class S3Store:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.minio_bucket
        self._cors_origins = settings.cors_origins
        self._client, self._presign_client = build_s3_clients(settings)

    async def ensure_bucket(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)
            if not self._cors_origins:
                return
            # MinIO may reject PutBucketCors; global CORS is configured in Helm values.
            with contextlib.suppress(ClientError):
                self._client.put_bucket_cors(
                    Bucket=self._bucket,
                    CORSConfiguration={
                        "CORSRules": [
                            {
                                "AllowedHeaders": ["*"],
                                "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                                "AllowedOrigins": self._cors_origins,
                                "ExposeHeaders": ["ETag"],
                                "MaxAgeSeconds": 3600,
                            }
                        ]
                    },
                )

        await asyncio.to_thread(_ensure)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

        return await asyncio.to_thread(_get)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        def _head() -> tuple[int, str | None]:
            try:
                obj = self._client.head_object(Bucket=self._bucket, Key=key)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise FileNotFoundError(key) from exc
                raise
            return int(obj.get("ContentLength") or 0), obj.get("ContentType")

        return await asyncio.to_thread(_head)

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes:
        def _get_range() -> bytes:
            obj = self._client.get_object(
                Bucket=self._bucket, Key=key, Range=f"bytes=0-{max(0, max_bytes - 1)}"
            )
            return obj["Body"].read()

        return await asyncio.to_thread(_get_range)

    async def presign_put(
        self, key: str, content_type: str, *, expires_seconds: int = 3600
    ) -> PresignedPut:
        url = await asyncio.to_thread(
            self._presign_client.generate_presigned_url,
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_seconds,
            HttpMethod="PUT",
        )
        return PresignedPut(upload_url=url, headers={"Content-Type": content_type})
