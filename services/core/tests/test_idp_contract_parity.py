"""Cross-service schema parity between ``repody_common`` and ``backend`` stage contracts."""

import importlib.util
from pathlib import Path
from types import ModuleType

from repody_common.contracts import ArtifactRef, CaseRef, IdpStageInput, IdpStageOutput


def _load_backend_stage_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[3]
    stage_path = repo_root / "backend" / "src" / "repody" / "schemas" / "stage.py"
    spec = importlib.util.spec_from_file_location("backend_stage_schema", stage_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_idp_stage_contracts_match_across_core_and_idp() -> None:
    backend_stage = _load_backend_stage_module()

    artifact = ArtifactRef(
        artifact_id="art-1",
        module="core",
        kind="source_document",
        storage_key="cases/case-1/doc.pdf",
        sha256="b" * 64,
        mime_type="application/pdf",
        byte_size=4096,
    )
    core_input = IdpStageInput(
        case=CaseRef(
            case_id="case-1",
            account_id="acc-1",
            external_ref="EXT-1",
            input_payload={"channel": "portal"},
            artifacts=[artifact],
        ),
        workflow_id="wf-1",
        artifacts=[artifact],
    )
    backend_input = backend_stage.IdpStageInput.model_validate_json(core_input.model_dump_json())
    assert backend_input.model_dump() == core_input.model_dump()

    backend_output = backend_stage.IdpStageOutput(
        idp_run_id="run-123",
        outcome="warning",
        extracted_data={"Invoice": {"total_amount": 500}},
        flagged_fields=["Invoice.total_amount"],
        pages_processed=2,
    )
    core_output = IdpStageOutput.model_validate_json(backend_output.model_dump_json())
    assert core_output.model_dump() == backend_output.model_dump()
