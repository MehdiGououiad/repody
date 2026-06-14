from __future__ import annotations

import re
import time

import structlog

from audit_workbench.inference.availability import inference_available
from audit_workbench.inference.factory import get_inference_client
from audit_workbench.inference.structured import chat_structured, parse_structured_response
from audit_workbench.inference.structured_models import LlmRuleBatchOutput, LlmRuleVerdict
from audit_workbench.inference.validation_model import resolve_llm_validation_model
from audit_workbench.settings import get_settings

_FEE_KEYWORDS = re.compile(
    r"late\s*fee|penalty|pénalité|penalite|retard|frais\s+de\s+retard",
    re.I,
)

RuleStatus = str  # passed | failed | skipped | error
log = structlog.get_logger()
_FIELD_REFERENCE = re.compile(
    r"(?<![\w@])@([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)"
)


def referenced_fields(body: str) -> list[str]:
    return list(dict.fromkeys(_FIELD_REFERENCE.findall(body or "")))


def _rule_field_values(
    body: str,
    field_values: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    references = referenced_fields(body)
    if not references:
        return field_values, []
    selected: dict[str, str] = {}
    missing: list[str] = []
    for reference in references:
        value = field_values.get(reference)
        if value is None:
            value = field_values.get(reference.lower())
        if value is None:
            missing.append(reference)
        else:
            selected[reference] = value
    return selected, missing


def _llm_disabled() -> bool:
    return not get_settings().llm_validation_enabled


def _llm_unavailable_status() -> RuleStatus:
    if _llm_disabled():
        return "skipped"
    mode = get_settings().inference_mode.lower()
    if mode == "stub":
        return "skipped"
    return "error"


def _llm_unavailable_detail() -> str:
    if _llm_disabled():
        return "LLM validation is disabled. Set AUDIT_LLM_VALIDATION_ENABLED=true and configure AUDIT_VALIDATION_MODEL."
    mode = get_settings().inference_mode.lower()
    if mode == "stub":
        return "LLM evaluator skipped (inference disabled)."
    return "LLM inference unavailable."


_LLM_RULE_FEW_SHOT = """
Examples:
Rule: "Verify @total_amount is positive."
Fields: total_amount=6000
→ {"passed":true,"detail":"total_amount is positive."}

Rule: "Ensure @vendor_name mentions Acme."
Fields: vendor_name=Globex Corp
→ {"passed":false,"detail":"vendor_name is Globex Corp, not Acme."}
""".strip()


def _verdict_to_status(verdict: LlmRuleVerdict) -> tuple[RuleStatus, str]:
    detail = (verdict.detail or "")[:500]
    if verdict.passed:
        return "passed", detail or "Passed."
    return "failed", detail or "Failed."


def _parse_pass_fail(raw: str) -> tuple[RuleStatus, str]:
    try:
        verdict = parse_structured_response(LlmRuleVerdict, raw)
        return _verdict_to_status(verdict)
    except ValueError:
        return "error", "LLM response was not valid JSON."


def _fields_block(field_values: dict[str, str]) -> str:
    lines = [f"{k}={v}" for k, v in field_values.items() if v and v != "—"]
    return "\n".join(lines[:40]) or "(no values)"


async def evaluate_llm_rule(
    body: str,
    field_values: dict[str, str],
    *,
    rule_name: str = "Rule",
    llm_model: str | None = None,
) -> tuple[RuleStatus, str]:
    """Text-only LLM validation on extracted fields (fast on CPU — no re-OCR)."""
    text = (body or "").strip()
    if not text:
        return "failed", "Rule body is empty — skipped."

    selected_fields, missing_fields = _rule_field_values(text, field_values)
    if missing_fields:
        missing = ", ".join(f"@{name}" for name in missing_fields)
        return "error", f"Unknown field reference(s): {missing}."

    if _FEE_KEYWORDS.search(text):
        for value in selected_fields.values():
            if value and value != "—" and _FEE_KEYWORDS.search(value):
                return (
                    "failed",
                    "Possible late-fee or penalty wording found in extracted field values.",
                )
        return "passed", "No late-fee or penalty keywords found in extracted values."

    if _llm_disabled():
        return _llm_unavailable_status(), _llm_unavailable_detail()

    model, model_error = resolve_llm_validation_model(llm_model)
    if model_error:
        return "error", model_error

    client = get_inference_client()
    if not await inference_available(client):
        return _llm_unavailable_status(), _llm_unavailable_detail()

    fields_block = _fields_block(selected_fields)
    prompt = (
        f"{_LLM_RULE_FEW_SHOT}\n\n"
        f'Audit rule "{rule_name}": {text}\n'
        f"Fields:\n{fields_block}\n"
        'JSON only: {"passed":true|false,"detail":"..."}'
    )
    settings = get_settings()
    try:
        if settings.structured_llm_enabled:
            verdict = await chat_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LlmRuleVerdict,
                model=model,
                max_tokens=settings.validation_max_tokens,
            )
            return _verdict_to_status(verdict)
        raw = await client.chat(
            [{"role": "user", "content": prompt}],
            max_tokens=settings.validation_max_tokens,
            temperature=0.0,
            model=model,
            format_json=True,
        )
    except Exception as exc:
        return "error", f"LLM inference failed: {exc!r}"[:500]
    return _parse_pass_fail(raw)


async def evaluate_llm_rules_batch(
    rules: list[dict],
    field_values: dict[str, str],
    *,
    llm_model: str | None = None,
) -> dict[str, tuple[RuleStatus, str]]:
    """One Docker Model Runner call for all LLM rules (major CPU savings vs N sequential calls)."""
    out: dict[str, tuple[RuleStatus, str]] = {}
    if not rules:
        return out

    remaining: list[dict] = []
    batch_fields: dict[str, str] = {}
    for rule in rules:
        rid = rule.get("id") or ""
        body = (rule.get("body") or "").strip()
        selected_fields, missing_fields = _rule_field_values(body, field_values)
        if missing_fields:
            missing = ", ".join(f"@{name}" for name in missing_fields)
            out[rid] = ("error", f"Unknown field reference(s): {missing}.")
            continue
        if _FEE_KEYWORDS.search(body):
            for value in selected_fields.values():
                if value and value != "—" and _FEE_KEYWORDS.search(value):
                    out[rid] = (
                        "failed",
                        "Possible late-fee or penalty wording found in extracted field values.",
                    )
                    break
            else:
                out[rid] = ("passed", "No late-fee or penalty keywords found in extracted values.")
        else:
            batch_fields.update(selected_fields)
            remaining.append(rule)

    if not remaining:
        return out

    if len(remaining) == 1:
        rule = remaining[0]
        rid = rule.get("id") or ""
        out[rid] = await evaluate_llm_rule(
            rule.get("body") or "",
            field_values,
            rule_name=rule.get("name") or "Rule",
            llm_model=llm_model,
        )
        return out

    if _llm_disabled():
        status = _llm_unavailable_status()
        detail = _llm_unavailable_detail()
        for rule in remaining:
            out[rule.get("id") or ""] = (status, detail)
        return out

    model, model_error = resolve_llm_validation_model(llm_model)
    if model_error:
        for rule in remaining:
            out[rule.get("id") or ""] = ("error", model_error)
        return out

    client = get_inference_client()
    if not await inference_available(client):
        status = _llm_unavailable_status()
        detail = _llm_unavailable_detail()
        for rule in remaining:
            out[rule.get("id") or ""] = (status, detail)
        return out

    fields_block = _fields_block(batch_fields)
    rules_block = "\n".join(
        f'- id="{r.get("id")}": {r.get("name")} — {(r.get("body") or "").strip()}'
        for r in remaining
    )
    prompt = (
        f"{_LLM_RULE_FEW_SHOT}\n\n"
        "Evaluate each audit rule against the field values.\n"
        f"Fields:\n{fields_block}\n\n"
        f"Rules:\n{rules_block}\n\n"
        "JSON only: "
        '{"results":[{"id":"<rule id>","passed":true|false,"detail":"..."}]}\n'
    )
    settings = get_settings()
    started = time.perf_counter()
    try:
        if settings.structured_llm_enabled:
            batch = await chat_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LlmRuleBatchOutput,
                model=model,
                max_tokens=min(256, settings.validation_max_tokens * max(1, len(remaining))),
            )
            for row in batch.results:
                out[row.id] = _verdict_to_status(
                    LlmRuleVerdict(passed=row.passed, detail=row.detail)
                )
        else:
            raw = await client.chat(
                [{"role": "user", "content": prompt}],
                max_tokens=min(256, settings.validation_max_tokens * max(1, len(remaining))),
                temperature=0.0,
                model=model,
                format_json=True,
            )
            batch = parse_structured_response(LlmRuleBatchOutput, raw)
            for row in batch.results:
                out[row.id] = _verdict_to_status(
                    LlmRuleVerdict(passed=row.passed, detail=row.detail)
                )
    except Exception as exc:
        detail = f"LLM inference failed: {exc!r}"[:500]
        for rule in remaining:
            out[rule.get("id") or ""] = ("error", detail)
        return out

    for rule in remaining:
        rid = rule.get("id") or ""
        if rid not in out:
            out[rid] = ("error", "LLM batch response omitted this rule.")
    log.info(
        "llm_rule_batch_done",
        model=model,
        rules=len(remaining),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        passed=sum(1 for status, _detail in out.values() if status == "passed"),
        failed=sum(1 for status, _detail in out.values() if status in ("failed", "error")),
    )
    return out
