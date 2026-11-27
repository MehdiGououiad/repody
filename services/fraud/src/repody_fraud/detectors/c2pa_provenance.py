"""Tier-1 Content Credentials (C2PA) provenance verification via official ``c2pa-python``."""

import io
import json
from typing import Any

import c2pa

from repody_common.contracts import FraudFinding

AI_SOURCE_MARKERS = (
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
    "c2pa.ai_generated",
)


def evaluate_c2pa_manifest(manifest_store: dict[str, Any]) -> list[FraudFinding]:
    """Evaluate a parsed C2PA manifest store dict into explainable forensic findings."""
    findings: list[FraudFinding] = []
    validation_status = manifest_store.get("validation_status") or []
    failed_codes = [
        str(entry.get("code", "unknown"))
        for entry in validation_status
        if isinstance(entry, dict) and entry.get("code")
    ]
    if failed_codes:
        findings.append(
            FraudFinding(
                detector="c2pa_provenance",
                tier=1,
                code="C2PA_MANIFEST_TAMPERED",
                severity="critical",
                title="C2PA Content Credentials failed verification",
                detail=f"Manifest validation errors: {', '.join(failed_codes)}.",
            )
        )

    active_id = manifest_store.get("active_manifest")
    manifests = manifest_store.get("manifests") or {}
    active = manifests.get(active_id) if isinstance(manifests, dict) and active_id else None
    assertions = (active or {}).get("assertions") or []

    ai_detected = False
    edited_actions: list[str] = []
    for assertion in assertions:
        if not isinstance(assertion, dict):
            continue
        blob = json.dumps(assertion).lower()
        if any(marker in blob for marker in AI_SOURCE_MARKERS):
            ai_detected = True
        if assertion.get("label", "").startswith("c2pa.actions"):
            actions = (assertion.get("data") or {}).get("actions") or []
            for act in actions:
                if isinstance(act, dict):
                    action_name = str(act.get("action", ""))
                    if action_name in (
                        "c2pa.edited",
                        "c2pa.cropped",
                        "c2pa.drawn",
                        "c2pa.filtered",
                    ):
                        edited_actions.append(action_name)

    if ai_detected:
        findings.append(
            FraudFinding(
                detector="c2pa_provenance",
                tier=1,
                code="C2PA_AI_GENERATED_MEDIA",
                severity="critical",
                title="C2PA manifest declares AI-generated media",
                detail="Active Content Credentials assert algorithmic/generative synthesis.",
            )
        )
    if edited_actions:
        findings.append(
            FraudFinding(
                detector="c2pa_provenance",
                tier=1,
                code="C2PA_EDITED_PROVENANCE",
                severity="medium",
                title="C2PA manifest records post-capture image editing",
                detail=f"Recorded C2PA actions: {', '.join(sorted(set(edited_actions)))}.",
            )
        )
    return findings


def analyze_c2pa_provenance(data: bytes, mime_type: str) -> list[FraudFinding]:
    """Read and validate embedded C2PA Content Credentials when present in media bytes."""
    supported = {m.lower() for m in c2pa.Reader.get_supported_mime_types()}
    if mime_type.lower() not in supported:
        return []
    try:
        reader = c2pa.Reader.try_create(format_or_path=mime_type, stream=io.BytesIO(data))
    except c2pa.C2paError:
        return []
    if reader is None:
        return []
    with reader:
        raw_json = reader.json()
    return evaluate_c2pa_manifest(json.loads(raw_json))
