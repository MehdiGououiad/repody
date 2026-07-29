from unittest.mock import MagicMock, patch

from audit_workbench.settings import Settings
from audit_workbench.infra.storage.s3 import build_s3_clients


def test_presign_uses_public_endpoint_client_when_configured() -> None:
    settings = Settings(
        minio_endpoint="minio:9000",
        minio_public_endpoint="localhost:9000",
        storage_backend="s3",
    )

    with patch("audit_workbench.infra.storage.s3.boto3.client") as mock_client:
        internal = MagicMock(name="internal")
        public = MagicMock(name="public")
        mock_client.side_effect = [internal, public]

        client, presign_client = build_s3_clients(settings)

    assert mock_client.call_count == 2
    assert client is internal
    assert presign_client is public


def test_presign_reuses_internal_client_when_endpoints_match() -> None:
    settings = Settings(
        minio_endpoint="localhost:9000",
        minio_public_endpoint=None,
        storage_backend="s3",
    )

    with patch("audit_workbench.infra.storage.s3.boto3.client") as mock_client:
        internal = MagicMock(name="internal")
        mock_client.return_value = internal

        client, presign_client = build_s3_clients(settings)

    assert mock_client.call_count == 1
    assert client is internal
    assert presign_client is internal
