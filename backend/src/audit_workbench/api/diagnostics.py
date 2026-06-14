from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import Field

from audit_workbench.extraction.document_model_branding import public_runtime_model_name
from audit_workbench.schemas.common import CamelModel
from audit_workbench.services.document_model_catalog import (
    probe_document_model_state,
    reachable_detail,
    run_generation_probe,
    unreachable_detail,
)
from audit_workbench.settings import get_settings

router = APIRouter(tags=["diagnostics"])


class OcrDiagnosticResponse(CamelModel):
    ok: bool
    model: str
    runtime: str = ""
    inference_reachable: bool = False
    model_runner_reachable: bool = False
    model_in_registry: bool = False
    model_loaded: bool = False
    extractor: str = ""
    inference_mode: str = ""
    infer_ms: int | None = None
    sample_extracted: bool = False
    detail: str = ""
    hint: str = ""
    settings: dict[str, int | float | str | bool] = Field(default_factory=dict)


@router.get("/diagnostics/ocr", response_model=OcrDiagnosticResponse)
async def ocr_diagnostic(
    run_infer: bool = Query(False, description="Run a short Repody VLM probe."),
) -> OcrDiagnosticResponse:
    """Document model runtime status (Docker Model Runner or vLLM)."""
    settings = get_settings()
    state = await probe_document_model_state(settings)
    snapshot: dict[str, int | float | str | bool] = {
        "extractor": settings.extractor,
        "inferenceMode": settings.inference_mode,
        "runtime": state.runtime,
        "documentModelMaxEdgePx": settings.repody_vlm_max_edge_px,
        "documentModelPdfDpi": settings.repody_vlm_pdf_dpi,
        "llmValidationEnabled": settings.llm_validation_enabled,
    }
    common = {
        "model": public_runtime_model_name(state.model),
        "runtime": state.runtime,
        "inference_reachable": state.reachable,
        "model_runner_reachable": state.reachable,
        "model_in_registry": state.model_loaded,
        "extractor": settings.extractor,
        "inference_mode": settings.inference_mode,
        "settings": snapshot,
    }
    if not state.reachable or not state.model_loaded:
        detail, hint = unreachable_detail(state.runtime)
        return OcrDiagnosticResponse(ok=False, detail=detail, hint=hint, **common)
    if not run_infer:
        return OcrDiagnosticResponse(
            ok=True,
            detail=reachable_detail(state.runtime, live_probe=settings.gpu_live_probe),
            hint="Add ?run_infer=true to run one billed GPU test.",
            **common,
        )

    probe = await run_generation_probe(settings)
    return OcrDiagnosticResponse(
        ok=probe.ok,
        model_loaded=True,
        infer_ms=probe.infer_ms,
        sample_extracted=True,
        detail=probe.detail,
        hint=probe.hint,
        **common,
    )
