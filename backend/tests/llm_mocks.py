"""Shared inference endpoint mocks for field extraction and validation."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import respx

from audit_workbench.inference.factory import get_inference_client
from audit_workbench.settings import get_settings

DEFAULT_BASE = "http://model-runner-mock.test/v1"

# Known fixture values keyed by normalized field name.
FIELD_FIXTURE_VALUES: dict[str, str] = {
    "total_amount": "6000.00",
    "prix_unitaire_ht": "5000.00",
    "unit_price": "5000.00",
    "subtotal": "5000.00",
    "tax": "1000.00",
    "tva": "1000.00",
    "grand_total": "6000.00",
    "contract_id": "ABC-991",
    "annual_fee": "12500.00",
    "note": "Sample diagnostic note",
    "reference_id": "REF-001",
    "line_total": "5625.00",
}


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _field_names_from_extraction_prompt(content: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r'-\s*"([^"]+)"', content):
        names.append(match.group(1))
    return names


def _build_extraction_json(content: str) -> str:
    fields: list[dict[str, Any]] = []
    for name in _field_names_from_extraction_prompt(content):
        norm = _normalize_key(name)
        value = FIELD_FIXTURE_VALUES.get(norm, "—")
        fields.append(
            {
                "name": name,
                "value": value,
                "confidence": 0.95 if value != "—" else None,
            }
        )
    if not fields:
        fields.append({"name": "note", "value": "mock", "confidence": 0.9})
    return json.dumps({"fields": fields})


def _rule_ids_from_batch_prompt(content: str) -> list[str]:
    return re.findall(r'- id="([^"]+)"', content)


def _build_combined_json(content: str) -> str:
    fields_json = _build_extraction_json(content)
    fields_data = json.loads(fields_json)
    rule_ids = _rule_ids_from_batch_prompt(content)
    return json.dumps(
        {
            "fields": fields_data.get("fields", []),
            "rule_results": [
                {"id": rid, "passed": True, "detail": "Rule check passed (mock)."}
                for rid in rule_ids
            ],
        }
    )


def inference_chat_side_effect(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode())
    user_content = ""
    for msg in payload.get("messages") or []:
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_content += str(part.get("text") or "")
            else:
                user_content += str(content or "")

    template_kwargs = payload.get("chat_template_kwargs") or {}
    template_raw = template_kwargs.get("template")
    if template_raw:
        try:
            template = json.loads(template_raw)
            if isinstance(template, dict) and template:
                mock_payload = {
                    key: FIELD_FIXTURE_VALUES.get(_normalize_key(key), "mock") for key in template
                }
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"role": "assistant", "content": json.dumps(mock_payload)}}
                        ]
                    },
                )
        except json.JSONDecodeError:
            pass

    if "rule_results" in user_content and "--- DOCUMENT TEXT ---" in user_content:
        content = _build_combined_json(user_content)
    elif "--- DOCUMENT TEXT ---" in user_content or "Output JSON only" in user_content:
        content = _build_extraction_json(user_content)
    elif "Evaluate each audit rule" in user_content:
        rule_ids = _rule_ids_from_batch_prompt(user_content)
        content = json.dumps(
            {
                "results": [
                    {"id": rid, "passed": True, "detail": "Rule check passed (mock)."}
                    for rid in rule_ids
                ]
            }
        )
    else:
        content = json.dumps({"passed": True, "detail": "Rule check passed (mock)."})

    return httpx.Response(
        200,
        json={"choices": [{"message": {"role": "assistant", "content": content}}]},
    )


def enable_dmr_mock(
    monkeypatch=None,
    *,
    base: str = DEFAULT_BASE,
) -> respx.MockRouter:
    """Point inference at a mocked OpenAI-compatible endpoint."""
    if monkeypatch is not None:
        monkeypatch.setenv("AUDIT_INFERENCE_MODE", "llamacpp")
        monkeypatch.setenv("AUDIT_LLAMACPP_BASE_URL", base)
    else:
        import os

        os.environ["AUDIT_INFERENCE_MODE"] = "llamacpp"
        os.environ["AUDIT_LLAMACPP_BASE_URL"] = base

    get_settings.cache_clear()
    get_inference_client.cache_clear()

    router = respx.mock(assert_all_called=False)
    router.get(f"{base}/models").mock(
        return_value=httpx.Response(200, json={"data": []}),
    )
    router.post(f"{base}/chat/completions").mock(side_effect=inference_chat_side_effect)
    router.start()
    return router


def disable_dmr_mock(router: respx.MockRouter | None) -> None:
    if router is not None:
        router.stop()
    get_inference_client.cache_clear()
    get_settings.cache_clear()


enable_ollama_mock = enable_dmr_mock
disable_ollama_mock = disable_dmr_mock
