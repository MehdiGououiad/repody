"""Document model catalog — registry entries plus optional live runtime probes."""

from __future__ import annotations

import time
from dataclasses import dataclass

from audit_workbench.extraction.document_model_branding import (
    REPODY_VLM_CATALOG_ID,
    normalize_public_catalog_id,
)
from audit_workbench.extraction.model_registry import (
    DocumentModelSpec,
    list_document_models,
    parse_document_model,
)
from audit_workbench.extraction.surya_ocr import (
    surya_inference_configured,
    surya_package_installed,
)
from audit_workbench.inference.openai_compat import (
    list_openai_models,
    model_is_available,
    ping_openai_compat,
    post_chat_completion,
)
from audit_workbench.inference.runtime import (
    default_document_runtime,
    openai_base_url_for_runtime,
    openai_probe_timeout_seconds,
)
from audit_workbench.settings import Settings, get_settings

RUNTIMES = ("docker_model_runner", "vllm", "surya")

SERVERLESS_CATALOG_NOTE = (
    "Serverless GPU — billed only on extraction runs (idle GPU probes disabled)."
)
SURYA_CATALOG_NOTE = (
    "Surya OCR 2 via llama-server (datalab-to/surya-ocr-2-gguf). "
    "Set AUDIT_SURYA_INFERENCE_URL and match SURYA_INFERENCE_PARALLEL to --parallel."
)


@dataclass(frozen=True)
class CatalogModelEntry:
    spec: DocumentModelSpec
    available: bool
    availability_note: str | None


@dataclass(frozen=True)
class RuntimeProbeResult:
    runtime: str
    model: str
    reachable: bool
    model_loaded: bool


@dataclass(frozen=True)
class GenerationProbeResult:
    ok: bool
    infer_ms: int
    detail: str
    hint: str = ""


async def installed_runtime_models(
    settings: Settings | None = None,
) -> dict[str, set[str]]:
    settings = settings or get_settings()
    installed: dict[str, set[str]] = {runtime: set() for runtime in RUNTIMES}
    if not settings.gpu_live_probe:
        return installed
    runtime = default_document_runtime(settings)
    base_url = openai_base_url_for_runtime(runtime, settings)
    if base_url.strip():
        installed[runtime] = await list_openai_models(
            base_url,
            timeout=openai_probe_timeout_seconds(base_url),
        )
    if surya_inference_configured(settings):
        surya_url = (settings.surya_inference_url or "").strip().rstrip("/")
        installed["surya"] = await list_openai_models(
            surya_url,
            timeout=openai_probe_timeout_seconds(surya_url),
        )
    return installed


def availability_for_spec(
    spec: DocumentModelSpec,
    *,
    installed_by_runtime: dict[str, set[str]],
    live_probe: bool = True,
    active_runtime: str | None = None,
) -> tuple[bool, str | None]:
    _ = active_runtime
    if not live_probe and spec.runtime in RUNTIMES:
        return True, SERVERLESS_CATALOG_NOTE
    runtime_models = installed_by_runtime.get(spec.runtime) or set()
    installed = model_is_available(spec.runtime_model or "", runtime_models)
    if spec.runtime == "docker_model_runner":
        note = None if installed else "Enable the document model runtime and install Repody VLM."
        return installed, note
    if spec.runtime == "vllm":
        if not live_probe:
            return True, SERVERLESS_CATALOG_NOTE
        note = None if installed else (
            "Start vLLM or llama-server and set AUDIT_VLLM_BASE_URL / AUDIT_VLLM_SERVED_MODEL."
        )
        return installed, note
    if spec.runtime == "surya":
        settings = get_settings()
        if not surya_package_installed():
            return False, "Install optional dependency surya-ocr (BACKEND_EXTRAS=otel,ocr on the worker image)."
        if not surya_inference_configured(settings):
            return False, (
                "Set AUDIT_SURYA_INFERENCE_URL to a pre-running llama-server "
                "(SURYA_INFERENCE_BACKEND=llamacpp). See deploy/llamacpp/README.md#surya-ocr-2."
            )
        if not live_probe:
            return True, SURYA_CATALOG_NOTE
        runtime_models = installed_by_runtime.get("surya") or set()
        installed = bool(runtime_models) or model_is_available(
            spec.runtime_model or "",
            runtime_models,
        )
        note = None if installed else (
            f"llama-server not reachable at {settings.surya_inference_url}. "
            "Run pnpm llamacpp:surya:serve on the host."
        )
        return installed, note
    return False, "Unsupported document model runtime."


async def list_catalog_with_availability(
    settings: Settings | None = None,
) -> tuple[list[CatalogModelEntry], str]:
    settings = settings or get_settings()
    live_probe = settings.gpu_live_probe
    active_runtime = default_document_runtime(settings)
    installed = await installed_runtime_models(settings)
    entries: list[CatalogModelEntry] = []
    for spec in list_document_models():
        available, note = availability_for_spec(
            spec,
            installed_by_runtime=installed,
            live_probe=live_probe,
            active_runtime=active_runtime,
        )
        entries.append(CatalogModelEntry(spec=spec, available=available, availability_note=note))

    default = normalize_public_catalog_id(settings.default_ocr_model)
    if not any(entry.spec.id == default and entry.available for entry in entries):
        fallback = next((entry for entry in entries if entry.available), None)
        if fallback is not None:
            default = fallback.spec.id
    return entries, default


async def probe_active_runtime(settings: Settings | None = None) -> bool | None:
    settings = settings or get_settings()
    if not settings.gpu_live_probe:
        return None
    mode = settings.inference_mode.lower()
    if mode not in RUNTIMES:
        return None
    runtime = "vllm" if mode == "vllm" else "docker_model_runner"
    base_url = openai_base_url_for_runtime(runtime, settings)
    return await ping_openai_compat(
        base_url,
        timeout=openai_probe_timeout_seconds(base_url, default=5.0),
    )


async def probe_document_model_state(
    settings: Settings | None = None,
) -> RuntimeProbeResult:

    settings = settings or get_settings()
    spec = parse_document_model(None)
    if not settings.gpu_live_probe:
        return RuntimeProbeResult(
            runtime=spec.runtime,
            model=spec.runtime_model,
            reachable=True,
            model_loaded=True,
        )
    base_url = openai_base_url_for_runtime(spec.runtime, settings)
    probe_timeout = openai_probe_timeout_seconds(base_url, default=5.0)
    installed = await list_openai_models(base_url, timeout=probe_timeout)
    reachable = bool(installed) or await ping_openai_compat(base_url, timeout=probe_timeout)
    loaded = model_is_available(spec.runtime_model, installed)
    return RuntimeProbeResult(
        runtime=spec.runtime,
        model=spec.runtime_model,
        reachable=reachable,
        model_loaded=loaded,
    )


def unreachable_detail(runtime: str) -> tuple[str, str]:
    if runtime == "docker_model_runner":
        return (
            "Repody VLM is unavailable.",
            "Run: pnpm models:pull",
        )
    return (
        "Repody VLM is unavailable on the GPU inference service.",
        "Check the external document-model runtime and wait for the served model to load.",
    )


def reachable_detail(runtime: str, *, live_probe: bool = True) -> str:
    if not live_probe:
        return "Live GPU probe disabled. Use ?run_infer=true to run one connectivity test."
    if runtime == "docker_model_runner":
        return "Document model runtime is reachable and Repody VLM is installed."
    return "GPU inference is reachable and Repody VLM is loaded."


def generation_failure_hint(runtime: str) -> str:
    if runtime == "docker_model_runner":
        return "Check Docker Model Runner logs with: docker model logs"
    return (
        "Check vLLM or llama-server logs on the inference host."
    )


async def run_generation_probe(
    settings: Settings | None = None,
) -> GenerationProbeResult:

    settings = settings or get_settings()
    spec = parse_document_model(None)
    base_url = openai_base_url_for_runtime(spec.runtime, settings)
    started = time.perf_counter()
    try:
        data = await post_chat_completion(
            base_url,
            {
                "model": spec.runtime_model,
                "messages": [
                    {
                        "role": "user",
                        "content": 'Return JSON only: {"warmup":true}',
                    }
                ],
                "max_tokens": 32,
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.repody_vlm_timeout_seconds,
        )
        raw = str(data["choices"][0]["message"]["content"])
        infer_ms = int((time.perf_counter() - started) * 1000)
        ok = '"warmup"' in raw and "true" in raw.lower()
        return GenerationProbeResult(
            ok=ok,
            infer_ms=infer_ms,
            detail=f"{spec.runtime} generation probe completed.",
        )
    except Exception as exc:
        return GenerationProbeResult(
            ok=False,
            infer_ms=int((time.perf_counter() - started) * 1000),
            detail=repr(exc),
            hint=generation_failure_hint(spec.runtime),
        )
