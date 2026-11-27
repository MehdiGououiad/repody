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
_EDIT_ACTIONS = frozenset({"c2pa.edited", "c2pa.cropped", "c2pa.drawn", "c2pa.filtered"})


def _extract_active_assertions(manifest_store: dict[str, Any]) -> list[dict[str, Any]]:
    active_id = manifest_store.get("active_manifest")
    manifests = manifest_store.get("manifests")
    if not isinstance(manifests, dict) or not active_id:
        return []
    active = manifests.get(active_id)
    if not isinstance(active, dict):
        return []
    assertions = active.get("assertions")
    if not isinstance(assertions, list):
        return []
    return [item for item in assertions if isinstance(item, dict)]


def _scan_assertions_for_provenance(assertions: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    ai_detected = False
    edited_actions: list[str] = []
    for assertion in assertions:
        blob = json.dumps(assertion).lower()
        if any(marker in blob for marker in AI_SOURCE_MARKERS):
            ai_detected = True
        if not str(assertion.get("label", "")).startswith("c2pa.actions"):
            continue
        data_obj = assertion.get("data")
        actions = data_obj.get("actions") if isinstance(data_obj, dict) else None
        if not isinstance(actions, list):
            continue
        for act in actions:
            action_name = str(act.get("action", "")) if isinstance(act, dict) else ""
            if action_name in _EDIT_ACTIONS:
                edited_actions.append(action_name)
    return ai_detected, edited_actions


def evaluate_c2pa_manifest(manifest_store: dict[str, Any]) -> list[FraudFinding]:
    """Evaluate a parsed C2PA manifest store dict into explainable forensic findings."""
    findings: list[FraudFinding] = []
    validation_status = manifest_store.get("validation_status") or []
    failed_codes = [
        str(entry["code"])
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

    assertions = _extract_active_assertions(manifest_store)
    ai_detected, edited_actions = _scan_assertions_for_provenance(assertions)
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
