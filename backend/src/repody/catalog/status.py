"""Is the NuExtract model served? One ``GET /v1/models`` on the llama-server."""

from __future__ import annotations

from dataclasses import dataclass

from repody.inference.openai_compat import list_openai_models, model_is_available
from repody.inference.runtime import llamacpp_base_url
from repody.settings import Settings, get_settings


@dataclass(frozen=True, slots=True)
class ModelStatus:
    reachable: bool
    loaded: bool


async def model_status(settings: Settings | None = None) -> ModelStatus:
    settings = settings or get_settings()
    installed = await list_openai_models(
        llamacpp_base_url(settings), timeout=5.0, api_key=settings.llamacpp_api_key
    )
    return ModelStatus(
        reachable=bool(installed),
        loaded=model_is_available(settings.llamacpp_served_model, installed),
    )
