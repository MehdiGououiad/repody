"""Tier-1 forensic detector tests: pikepdf, pypdfium2 revision diff, pyHanko, c2pa, pHash."""

from tests.conftest import (
    make_clean_jpeg,
    make_clean_pdf,
    make_js_pdf,
    make_tampered_incremental_pdf,
)

from repody_fraud.detectors.c2pa_provenance import analyze_c2pa_provenance, evaluate_c2pa_manifest
from repody_fraud.detectors.fingerprint import compute_document_fingerprints, hamming_distance
from repody_fraud.detectors.pdf_revision_diff import analyze_pdf_revision_diff
from repody_fraud.detectors.pdf_signatures import analyze_pdf_signatures
from repody_fraud.detectors.pdf_structure import analyze_pdf_structure


def test_clean_pdf_passes_tier1_structure_and_diff() -> None:
    pdf = make_clean_pdf()
    assert analyze_pdf_structure(pdf) == []
    assert analyze_pdf_signatures(pdf) == []
    diff = analyze_pdf_revision_diff(pdf)
    assert diff.findings == []
    assert diff.evidence == []


def test_tampered_incremental_pdf_flags_all_artifacts() -> None:
    tampered = make_tampered_incremental_pdf()
    struct_findings = analyze_pdf_structure(tampered)
    codes = {f.code for f in struct_findings}
    assert {
        "PDF_INCREMENTAL_UPDATES",
        "PDF_SUSPICIOUS_PRODUCER",
        "PDF_METADATA_MISMATCH",
    }.issubset(codes)

    diff = analyze_pdf_revision_diff(tampered)
    assert len(diff.findings) == 1
    assert diff.findings[0].code == "PDF_REVISION_VISUAL_CHANGE"
    assert diff.findings[0].severity == "critical"
    assert diff.findings[0].bbox is not None
    assert len(diff.evidence) == 1
    assert diff.evidence[0][1].data.startswith(b"\x89PNG")


def test_embedded_javascript_pdf_is_flagged() -> None:
    js_pdf = make_js_pdf()
    codes = {f.code for f in analyze_pdf_structure(js_pdf)}
    assert "PDF_EMBEDDED_JAVASCRIPT" in codes


def test_c2pa_manifest_evaluation_handles_tampered_ai_and_clean_jpeg() -> None:
    clean = make_clean_jpeg()
    assert analyze_c2pa_provenance(clean, "image/jpeg") == []

    manifest = {
        "validation_status": [{"code": "assertion.dataHash.mismatch"}],
        "active_manifest": "urn:uuid:1234",
        "manifests": {
            "urn:uuid:1234": {
                "assertions": [
                    {
                        "label": "c2pa.actions",
                        "data": {
                            "actions": [
                                {"action": "c2pa.edited"},
                                {
                                    "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
                                },
                            ]
                        },
                    }
                ]
            }
        },
    }
    findings = evaluate_c2pa_manifest(manifest)
    codes = {f.code for f in findings}
    assert codes == {
        "C2PA_MANIFEST_TAMPERED",
        "C2PA_AI_GENERATED_MEDIA",
        "C2PA_EDITED_PROVENANCE",
    }


def test_document_fingerprints_are_deterministic_bitstrings() -> None:
    pdf_a = make_clean_pdf("TEMPLATE A")
    fps_1 = compute_document_fingerprints(pdf_a, "application/pdf")
    fps_2 = compute_document_fingerprints(pdf_a, "application/pdf")
    assert len(fps_1) == 1
    assert len(fps_1[0].phash_bits) == 64
    assert set(fps_1[0].phash_bits) <= {"0", "1"}
    assert hamming_distance(fps_1[0].phash_bits, fps_2[0].phash_bits) == 0
