from fastapi import APIRouter

from repody.api.deps import SessionDep
from repody.app.rules_library import list_rule_templates
from repody.schemas.rules_library import RuleLibraryResponse

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/library", response_model=RuleLibraryResponse)
async def rules_library(session: SessionDep):
    return RuleLibraryResponse(rules=await list_rule_templates(session))
