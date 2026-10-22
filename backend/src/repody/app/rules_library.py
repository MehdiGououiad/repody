"""Reusable rule templates shown in the workflow builder."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import RuleTemplate
from repody.infra.db.seed import default_rule_templates
from repody.schemas.workflow import RuleTemplateSchema
from repody.settings import get_settings


async def _load_or_seed_templates(session: AsyncSession) -> list[RuleTemplate]:
    rows = list((await session.execute(select(RuleTemplate))).scalars().all())
    if rows:
        return rows
    session.add_all(default_rule_templates())
    await session.commit()
    return list((await session.execute(select(RuleTemplate))).scalars().all())


async def list_rule_templates(session: AsyncSession) -> list[RuleTemplateSchema]:
    """Return templates, seeding defaults on first use; LLM templates only when enabled."""
    llm_enabled = get_settings().llm_validation_enabled
    return [
        RuleTemplateSchema(
            id=t.id,
            name=t.name,
            kind=t.kind,
            scope=t.scope,
            description=t.description,
            body=t.body,
            severity=t.severity,
        )
        for t in await _load_or_seed_templates(session)
        if llm_enabled or (t.kind or "logic").lower() != "llm"
    ]
