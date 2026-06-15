from __future__ import annotations

from fastapi import APIRouter

from audit_workbench.services.unified_models_catalog import ModelsCatalogResponse, build_models_catalog

router = APIRouter(tags=["models"])


@router.get("/models/catalog", response_model=ModelsCatalogResponse)
async def list_models_catalog() -> ModelsCatalogResponse:
    """Unified document + validation model catalog with live availability."""
    return await build_models_catalog()
