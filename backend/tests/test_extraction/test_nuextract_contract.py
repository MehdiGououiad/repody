from audit_workbench.extraction.nuextract_contract import extraction_inference_profile_key
from audit_workbench.settings import Settings


def test_extraction_inference_profile_key():
    settings = Settings(llamacpp_served_model="numind/NuExtract3")
    key = extraction_inference_profile_key(settings=settings)
    assert key == "nuextract:official:model:numind/nuextract3"
