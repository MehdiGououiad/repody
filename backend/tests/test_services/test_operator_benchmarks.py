from __future__ import annotations

import json

import pytest

from audit_workbench.services.operator_benchmark_requests import (
    OperatorRequestError,
    parse_benchmark_options,
    resolve_benchmark_inputs,
    safe_model_identifier,
)
from audit_workbench.services.operator_benchmarks import benchmark_command


class FakeUpload:
    def __init__(self, filename: str, data: bytes) -> None:
        self.filename = filename
        self._data = data

    async def read(self) -> bytes:
        return self._data


def test_safe_model_identifier_rejects_shell_like_values() -> None:
    with pytest.raises(OperatorRequestError) as exc:
        safe_model_identifier("model; rm -rf /")

    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid model identifier."


def test_parse_benchmark_options_validates_model_array() -> None:
    with pytest.raises(OperatorRequestError) as exc:
        parse_benchmark_options(
            profile="models",
            models=json.dumps(["repody:vlm"] * 13),
            validation_mode="logic_only",
            warm_runs=1,
            minimum_accuracy=1.0,
            cache_check=True,
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "Select at most 12 models."


def test_benchmark_command_uses_cache_flag_and_models(tmp_path) -> None:
    command = benchmark_command(
        document=tmp_path / "doc.pdf",
        manifest=tmp_path / "manifest.json",
        output_dir=tmp_path / "out",
        profile="models",
        models=["repody:vlm", "vendor/model"],
        validation_mode="logic_only",
        warm_runs=1,
        minimum_accuracy=0.95,
        cache_check=False,
        judge_quality=False,
    )

    assert "--no-cache-check" in command
    assert "--cache-check" not in command
    assert command.count("--model") == 2
    assert command[-2:] == ["--model", "vendor/model"]


@pytest.mark.asyncio
async def test_resolve_benchmark_inputs_document_only_writes_auto_manifest(tmp_path) -> None:
    inputs = await resolve_benchmark_inputs(
        document=FakeUpload("scan.png", b"\x89PNG\r\n"),
        manifest=None,
        root=tmp_path,
        max_upload_bytes=1024,
    )

    assert inputs.document_path.is_file()
    assert inputs.manifest_path.is_file()
    manifest = json.loads(inputs.manifest_path.read_text(encoding="utf-8"))
    assert manifest["documentType"] == "Document"
    assert manifest["mimeType"] == "image/png"
    assert manifest["fields"] == []


@pytest.mark.asyncio
async def test_resolve_benchmark_inputs_rejects_invalid_manifest(tmp_path) -> None:
    with pytest.raises(OperatorRequestError) as exc:
        await resolve_benchmark_inputs(
            document=FakeUpload("invoice.pdf", b"%PDF-1.4\n%%EOF"),
            manifest=FakeUpload("manifest.json", b"{bad-json"),
            root=tmp_path,
            max_upload_bytes=1024,
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "Benchmark manifest must be valid JSON."


@pytest.mark.asyncio
async def test_resolve_benchmark_inputs_writes_sanitized_uploads(tmp_path) -> None:
    inputs = await resolve_benchmark_inputs(
        document=FakeUpload("invoice weird!.pdf", b"%PDF-1.4\n%%EOF"),
        manifest=FakeUpload("manifest.json", b'{"fields": []}'),
        root=tmp_path,
        max_upload_bytes=1024,
    )

    assert inputs.document_path.is_file()
    assert inputs.manifest_path.is_file()
    assert inputs.document_path.parent == tmp_path / "inputs"
    assert inputs.document_path.name.startswith("invoice-weird")
    assert json.loads(inputs.manifest_path.read_text(encoding="utf-8")) == {"fields": []}
