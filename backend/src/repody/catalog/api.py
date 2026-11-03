"""The one document model (NuExtract3 on the llama-server) and its live status."""

from __future__ import annotations

from repody.catalog.status import model_status
from repody.schemas.models_catalog import CatalogModelEntry, ModelsCatalogResponse
from repody.settings import get_settings

MODEL_ID = "repody:vlm"
MODEL_LABEL = "Repody VLM"
MODEL_DESCRIPTION = (
    "NuExtract3 structured extraction from page images (local llama-server, "
    "OpenAI-compatible). Optional Markdown transcription."
)


async def fetch_models_catalog() -> ModelsCatalogResponse:
    settings = get_settings()
    status = await model_status(settings)
    note = None
    if not status.reachable:
        note = "llama-server is not reachable — start it with `pnpm llamacpp:serve`."
    elif not status.loaded:
        note = f"llama-server does not serve {settings.llamacpp_served_model!r}."
    return ModelsCatalogResponse(
        models=[
            CatalogModelEntry(
                id=MODEL_ID,
                label=MODEL_LABEL,
                description=MODEL_DESCRIPTION,
                served_model=settings.llamacpp_served_model,
                available=status.loaded,
                availability_note=note,
            )
        ]
    )
