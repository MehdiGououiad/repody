from functools import lru_cache

from audit_workbench.extraction.base import DocumentExtractor
from audit_workbench.extraction.pipeline import PipelineExtractor
from audit_workbench.extraction.stub import StubDocumentExtractor
from audit_workbench.settings import get_settings


@lru_cache
def get_extractor() -> DocumentExtractor:
    name = get_settings().extractor.lower()
    if name == "stub":
        return StubDocumentExtractor()
    return PipelineExtractor()
