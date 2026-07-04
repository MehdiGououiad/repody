from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.db.models import RuleTemplate
from audit_workbench.db.seed import RULE_TEMPLATES
from audit_workbench.schemas.rules_library import RuleLibraryResponse
from audit_workbench.schemas.workflow import RuleTemplateSchema
from audit_workbench.settings import get_settings

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/library", response_model=RuleLibraryResponse)
async def rules_library(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(RuleTemplate))
    rows = result.scalars().all()
    if not rows:
        for tpl in RULE_TEMPLATES:
            session.add(tpl)
        await session.flush()
        result = await session.execute(select(RuleTemplate))
        rows = result.scalars().all()
    llm_enabled = get_settings().llm_validation_enabled
    rules = [
        RuleTemplateSchema(
            id=t.id,
            name=t.name,
            kind=t.kind,
            scope=t.scope,
            description=t.description,
            body=t.body,
            severity=t.severity,
        )
        for t in rows
        if llm_enabled or (t.kind or "logic").lower() != "llm"
    ]
    return RuleLibraryResponse(rules=rules)
