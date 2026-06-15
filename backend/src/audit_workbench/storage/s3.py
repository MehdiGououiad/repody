from __future__ import annotations

import asyncio

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from audit_workbench.settings import Settings
from audit_workbench.storage.base import ObjectStorage, PresignedPut


class S3ObjectStorage(ObjectStorage):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._bucket = settings.minio_bucket
        internal_endpoint = self._endpoint(settings)
        public_endpoint = self._public_endpoint(settings)
        self._client = self._make_client(internal_endpoint, settings)
        self._presign_client = (
            self._client
            if internal_endpoint == public_endpoint
            else self._make_client(public_endpoint, settings)
        )

    @staticmethod
    def _make_client(endpoint_url: str, settings: Settings):
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    @staticmethod
    def _endpoint(settings: Settings) -> str:
        # In-cluster MinIO listens on HTTP; TLS for browser uploads is at the edge (Caddy).
        return f"http://{settings.minio_endpoint}"

    @staticmethod
    def _public_endpoint(settings: Settings) -> str:
        if settings.minio_public_endpoint:
            raw = settings.minio_public_endpoint.strip()
            if raw.startswith("http://") or raw.startswith("https://"):
                return raw.rstrip("/")
            scheme = "https" if settings.minio_secure else "http"
            return f"{scheme}://{raw.rstrip('/')}"
        return S3ObjectStorage._endpoint(settings)

    def _ensure_cors(self) -> None:
        origins = self._settings.cors_origins
        if not origins:
            return
        try:
            self._client.put_bucket_cors(
                Bucket=self._bucket,
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
            # MinIO may reject PutBucketCors; global CORS is configured in compose.
            pass

    async def ensure_bucket(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket)
            self._ensure_cors()

        await asyncio.to_thread(_ensure)

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_put)
        return key

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
            return obj["Body"].read()

        return await asyncio.to_thread(_get)

    async def stat_object(self, key: str) -> tuple[int, str | None]:
        def _head() -> tuple[int, str | None]:
            try:
                obj = self._client.head_object(Bucket=self._bucket, Key=key)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise FileNotFoundError(key) from exc
                raise
            size = int(obj.get("ContentLength") or 0)
            content_type = obj.get("ContentType")
            return size, content_type

        return await asyncio.to_thread(_head)

    async def get_range_bytes(self, key: str, *, start: int, end: int) -> bytes:
        def _get_range() -> bytes:
            byte_range = f"bytes={start}-{max(start, end - 1)}"
            obj = self._client.get_object(Bucket=self._bucket, Key=key, Range=byte_range)
            return obj["Body"].read()

        return await asyncio.to_thread(_get_range)

    async def head_bytes(self, key: str, *, max_bytes: int = 4096) -> bytes:
        return await self.get_range_bytes(key, start=0, end=max_bytes)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            self._client.delete_object(Bucket=self._bucket, Key=key)

        await asyncio.to_thread(_delete)

    async def presign_put(
        self,
        key: str,
        content_type: str,
        *,
        expires_seconds: int = 3600,
    ) -> PresignedPut:
        def _presign() -> str:
            return self._presign_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
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
