import pytest

from audit_workbench.storage.local import LocalObjectStorage


@pytest.mark.asyncio
async def test_local_put_get(tmp_path):
    storage = LocalObjectStorage(tmp_path, "test-bucket")
    await storage.ensure_bucket()
    key = "uploads/demo.pdf"
    await storage.put_bytes(key, b"%PDF-1.4", "application/pdf")
    data = await storage.get_bytes(key)
    assert data.startswith(b"%PDF")
