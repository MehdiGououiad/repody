from unittest.mock import MagicMock, patch

from audit_workbench.settings import Settings
from audit_workbench.storage.s3 import S3ObjectStorage


def test_presign_uses_public_endpoint_client_when_configured() -> None:
    settings = Settings(
        minio_endpoint="minio:9000",
        minio_public_endpoint="localhost:9000",
        storage_backend="s3",
    )

    with patch("audit_workbench.storage.s3.boto3.client") as mock_client:
        internal = MagicMock(name="internal")
        public = MagicMock(name="public")
        public.generate_presigned_url.return_value = "http://localhost:9000/bucket/key?sig=abc"
        mock_client.side_effect = [internal, public]

        storage = S3ObjectStorage(settings)

    assert mock_client.call_count == 2
    assert storage._client is internal
    assert storage._presign_client is public


def test_presign_reuses_internal_client_when_endpoints_match() -> None:
    settings = Settings(
        minio_endpoint="localhost:9000",
        minio_public_endpoint=None,
        storage_backend="s3",
    )

    with patch("audit_workbench.storage.s3.boto3.client") as mock_client:
        internal = MagicMock(name="internal")
        mock_client.return_value = internal

        storage = S3ObjectStorage(settings)

    assert mock_client.call_count == 1
    assert storage._presign_client is internal
