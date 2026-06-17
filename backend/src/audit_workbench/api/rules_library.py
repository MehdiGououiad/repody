from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.db.models import RuleTemplate
from audit_workbench.schemas.workflow import RuleTemplateSchema


class RuleLibraryResponse(BaseModel):
    rules: list[RuleTemplateSchema] = Field(default_factory=list)


router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/library", response_model=RuleLibraryResponse)
async def rules_library(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(RuleTemplate))
    rows = result.scalars().all()
    if not rows:
        from audit_workbench.db.seed import RULE_TEMPLATES

        for tpl in RULE_TEMPLATES:
            session.add(tpl)
        await session.flush()
        result = await session.execute(select(RuleTemplate))
        rows = result.scalars().all()
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
    ]
    return RuleLibraryResponse(rules=rules)
