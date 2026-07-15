from __future__ import annotations

import time

import structlog

from audit_workbench.inference.availability import inference_available
from audit_workbench.inference.factory import get_inference_client
from audit_workbench.inference.structured import chat_structured, parse_structured_response
from audit_workbench.inference.structured_models import LlmRuleBatchOutput, LlmRuleVerdict
from audit_workbench.inference.validation_model import resolve_llm_validation_model
from audit_workbench.rules.llm_fields import (
    RuleStatus,
    evaluate_fee_keyword_rule,
    referenced_fields,
    rule_field_values,
    unknown_reference_detail,
)
from audit_workbench.rules.llm_prompts import batch_rules_prompt, single_rule_prompt
from audit_workbench.settings import get_settings

log = structlog.get_logger()

__all__ = [
    "evaluate_llm_rule",
    "evaluate_llm_rules_batch",
    "referenced_fields",
]


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
        return (
            "LLM validation is disabled. Set AUDIT_LLM_VALIDATION_ENABLED=true "
            "and configure AUDIT_VALIDATION_MODEL."
        )
    mode = get_settings().inference_mode.lower()
    if mode == "stub":
        return "LLM evaluator skipped (inference disabled)."
    return "LLM inference unavailable."


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


async def evaluate_llm_rule(
    body: str,
    field_values: dict[str, str],
    *,
    rule_name: str = "Rule",
    llm_model: str | None = None,
) -> tuple[RuleStatus, str]:
    """Text-only LLM validation on extracted fields (fast on CPU - no re-extraction)."""
    text = (body or "").strip()
    if not text:
        return "failed", "Rule body is empty \u2014 skipped."

    selected_fields, missing_fields = rule_field_values(text, field_values)
    if missing_fields:
        return "error", unknown_reference_detail(missing_fields)

    if fee_result := evaluate_fee_keyword_rule(text, selected_fields):
        return fee_result

    if _llm_disabled():
        return _llm_unavailable_status(), _llm_unavailable_detail()

    model, model_error = resolve_llm_validation_model(llm_model)
    if model_error:
        return "error", model_error

    client = get_inference_client()
    if not await inference_available(client):
        return _llm_unavailable_status(), _llm_unavailable_detail()

    prompt = single_rule_prompt(rule_name=rule_name, body=text, field_values=selected_fields)
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
    """One inference call for all LLM rules (major savings vs N sequential calls)."""
    out: dict[str, tuple[RuleStatus, str]] = {}
    if not rules:
        return out

    remaining: list[dict] = []
    batch_fields: dict[str, str] = {}
    for rule in rules:
        rule_id = rule.get("id") or ""
        body = (rule.get("body") or "").strip()
        selected_fields, missing_fields = rule_field_values(body, field_values)
        if missing_fields:
            out[rule_id] = ("error", unknown_reference_detail(missing_fields))
            continue
        if fee_result := evaluate_fee_keyword_rule(body, selected_fields):
            out[rule_id] = fee_result
            continue
        batch_fields.update(selected_fields)
        remaining.append(rule)

    if not remaining:
        return out

    if len(remaining) == 1:
        rule = remaining[0]
        rule_id = rule.get("id") or ""
        out[rule_id] = await evaluate_llm_rule(
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

    prompt = batch_rules_prompt(rules=remaining, field_values=batch_fields)
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
        rule_id = rule.get("id") or ""
        if rule_id not in out:
            out[rule_id] = ("error", "LLM batch response omitted this rule.")
    log.info(
        "llm_rule_batch_done",
        model=model,
        rules=len(remaining),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        passed=sum(1 for status, _detail in out.values() if status == "passed"),
        failed=sum(1 for status, _detail in out.values() if status in ("failed", "error")),
    )
    return out
