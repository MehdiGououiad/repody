"""S3/MinIO object store as plain functions + ObjectStore binder."""

from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from audit_workbench.settings import Settings
from audit_workbench.storage.base import ObjectStore, PresignedPut


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
        if raw.startswith("http://") or raw.startswith("https://"):
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


def build_s3_store(settings: Settings) -> ObjectStore:
    bucket = settings.minio_bucket
    client, presign_client = build_s3_clients(settings)

    def _ensure_cors() -> None:
        origins = settings.cors_origins
        if not origins:
            return
        try:
            client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedHeaders": ["*"],
                            "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                            "AllowedOrigins": origins,
                            "ExposeHeaders": ["ETag"],
                            "MaxAgeSeconds": 3600,
                        }
                    ]
                },
            )
        except ClientError:
            # MinIO may reject PutBucketCors; global CORS is configured in Helm values.
            pass

    async def ensure_bucket() -> None:
        def _ensure() -> None:
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError:
                client.create_bucket(Bucket=bucket)
            _ensure_cors()

        await asyncio.to_thread(_ensure)

    async def put_bytes(key: str, data: bytes, content_type: str) -> str:
        def _put() -> None:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_put)
        return key

    async def get_bytes(key: str) -> bytes:
        def _get() -> bytes:
            obj = client.get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()

        return await asyncio.to_thread(_get)

    async def stat_object(key: str) -> tuple[int, str | None]:
        def _head() -> tuple[int, str | None]:
            try:
                obj = client.head_object(Bucket=bucket, Key=key)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise FileNotFoundError(key) from exc
                raise
            size = int(obj.get("ContentLength") or 0)
            content_type = obj.get("ContentType")
            return size, content_type

        return await asyncio.to_thread(_head)

    async def get_range_bytes(key: str, *, start: int, end: int) -> bytes:
        def _get_range() -> bytes:
            byte_range = f"bytes={start}-{max(start, end - 1)}"
            obj = client.get_object(Bucket=bucket, Key=key, Range=byte_range)
            return obj["Body"].read()

        return await asyncio.to_thread(_get_range)

    async def head_bytes(key: str, *, max_bytes: int = 4096) -> bytes:
        return await get_range_bytes(key, start=0, end=max_bytes)

    async def delete(key: str) -> None:
        def _delete() -> None:
            client.delete_object(Bucket=bucket, Key=key)

        await asyncio.to_thread(_delete)

    async def presign_put(
        key: str,
        content_type: str,
        *,
        expires_seconds: int = 3600,
    ) -> PresignedPut:
        def _presign() -> str:
            return presign_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_seconds,
                HttpMethod="PUT",
            )

        url = await asyncio.to_thread(_presign)
        return PresignedPut(
            upload_url=url,
            method="PUT",
            headers={"Content-Type": content_type},
        )

    return ObjectStore(
        ensure_bucket=ensure_bucket,
        put_bytes=put_bytes,
        get_bytes=get_bytes,
        delete=delete,
        stat_object=stat_object,
        head_bytes=head_bytes,
        get_range_bytes=get_range_bytes,
        presign_put=presign_put,
    )
