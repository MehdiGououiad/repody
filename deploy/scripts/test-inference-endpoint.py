"""Thorough Repody-style inference endpoint compatibility test."""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import urllib.error
import urllib.request

from PIL import Image


def get_json(url: str, *, timeout: int = 15) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode())


def get_text(url: str, *, timeout: int = 15) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.status, resp.read().decode()


def post_json(base_url: str, path: str, payload: dict, *, timeout: int = 300) -> tuple[int, dict]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"error": {"message": raw}}
        return exc.code, body


def jpeg_b64(*, width: int = 64, height: int = 64, color: str = "white") -> str:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def msg_content(body: dict) -> str:
    message = (body.get("choices") or [{}])[0].get("message") or {}
    return (message.get("content") or "").strip()


def msg_reasoning(body: dict) -> str:
    message = (body.get("choices") or [{}])[0].get("message") or {}
    return (message.get("reasoning_content") or "").strip()


def parse_json_loose(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if "{" not in text:
            raise
        start = text.find("{")
        end = text.rfind("}") + 1
        parsed = json.loads(text[start:end])
    if not isinstance(parsed, dict):
        raise ValueError("expected JSON object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:5005")
    args = parser.parse_args()

    host = args.host.rstrip("/")
    base = f"{host}/v1"
    failures: list[str] = []
    warnings: list[str] = []
    passed: list[str] = []
    model: str | None = None
    vision = False

    print("=" * 60)
    print("Repody inference thorough retest @", host)
    print("=" * 60)

    print("\n[1] Health")
    for path in ("/health", "/v1/health"):
        try:
            status, body = get_text(f"{host}{path}")
            ok = status == 200 and "ok" in body.lower()
            print(f"  {path}: {status} {body[:80]}")
            if ok:
                passed.append(path)
            else:
                failures.append(f"{path} unexpected: {body[:120]}")
        except Exception as exc:
            failures.append(f"{path}: {exc}")
            print(f"  {path}: FAIL {exc}")

    print("\n[2] /v1/models")
    try:
        _, models = get_json(f"{base}/models")
        ids = [item["id"] for item in models.get("data", [])]
        print("  models:", ids)
        model = next((item for item in ids if "nuextract" in item.lower()), ids[0] if ids else None)
        if not model:
            failures.append("no model in /v1/models")
        else:
            passed.append("model listed")
            if (!/q4_k_m/i.test(model) && !/q8_0/i.test(model)) {
                warnings.append(f"model id {model!r} — expected nuextract3-q4_k_m or q8_0 alias")
    except Exception as exc:
        failures.append(f"/v1/models: {exc}")
        model = "nuextract3-q4_k_m"

    print("\n[3] /props (load config)")
    try:
        _, props = get_json(f"{host}/props")
        n_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        modalities = props.get("modalities") or {}
        vision = bool(modalities.get("vision"))
        model_path = props.get("model_path", "")
        chat_caps = props.get("chat_template_caps") or {}
        print(f"  model_path: {model_path}")
        print(f"  n_ctx: {n_ctx}")
        print(f"  vision: {vision}")
        print(f"  chat_template_caps: {chat_caps}")
        if n_ctx is None:
            warnings.append("n_ctx not reported in props")
        elif n_ctx < 16384:
            failures.append(f"n_ctx {n_ctx} < 16384 (Repody target)")
        else:
            passed.append(f"n_ctx >= 16384 ({n_ctx})")
        if not vision:
            failures.append("vision is false — mmproj not loaded")
        else:
            passed.append("vision enabled")
        if "nuextract" not in model_path.lower():
            warnings.append("model_path does not mention nuextract")
    except Exception as exc:
        failures.append(f"/props: {exc}")

    assert model is not None

    print("\n[4] Text smoke (temp=0.2, enable_thinking=false)")
    status, body = post_json(
        base,
        "/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
            "max_tokens": 32,
            "temperature": 0.2,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=120,
    )
    text = msg_content(body)
    reasoning = msg_reasoning(body)
    print(f"  HTTP {status}, content={text!r}, reasoning_len={len(reasoning)}")
    if status != 200:
        failures.append(f"text smoke HTTP {status}: {body}")
    elif "ok" not in text.lower():
        failures.append(f"text smoke bad content: {text!r} (reasoning={reasoning[:100]!r})")
    else:
        passed.append("text smoke")

    img = jpeg_b64()

    print("\n[5] Warmup (image + chat_template_kwargs, Repody-style)")
    status, body = post_json(
        base,
        "/chat/completions",
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                    ],
                }
            ],
            "max_tokens": 64,
            "temperature": 0.0,
            "stream": False,
            "chat_template_kwargs": {
                "template": json.dumps({"warmup": "verbatim-string"}),
                "instructions": "Warm up the model. Return null when the field is absent.",
                "enable_thinking": False,
            },
        },
        timeout=300,
    )
    warmup_text = msg_content(body)
    print(f"  HTTP {status}, response={warmup_text[:240]!r}")
    if status != 200:
        err = (body.get("error") or {}).get("message", body)
        failures.append(f"warmup HTTP {status}: {err}")
    else:
        try:
            parsed = parse_json_loose(warmup_text)
            print(f"  parsed JSON: {parsed}")
            passed.append("warmup JSON")
        except Exception:
            failures.append("warmup not valid JSON (kwargs ignored?)")

    print("\n[6] Extract (text+image + template kwargs)")
    status, body = post_json(
        base,
        "/chat/completions",
        {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract structured data from this document."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}},
                    ],
                }
            ],
            "max_tokens": 256,
            "temperature": 0.2,
            "chat_template_kwargs": {
                "template": json.dumps({"vendor": "verbatim-string", "total": "number"}),
                "instructions": "Field instructions:\n- `vendor`: seller name\n- `total`: amount",
                "enable_thinking": False,
            },
        },
        timeout=300,
    )
    extract_text = msg_content(body)
    print(f"  HTTP {status}, response={extract_text[:320]!r}")
    if status != 200:
        err = (body.get("error") or {}).get("message", body)
        failures.append(f"extract HTTP {status}: {err}")
    else:
        try:
            parsed = parse_json_loose(extract_text)
            print(f"  parsed JSON: {parsed}")
            passed.append("multimodal extract")
        except Exception:
            failures.append("extract response not JSON")

    print("\n[7] Text-only structured extract (kwargs sanity)")
    status, body = post_json(
        base,
        "/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "user", "content": "Document: Invoice from ACME Corp, total 42.50 EUR"}
            ],
            "max_tokens": 128,
            "temperature": 0.2,
            "chat_template_kwargs": {
                "template": json.dumps({"vendor": "verbatim-string", "total": "number"}),
                "instructions": "Extract fields. Return null when absent.",
                "enable_thinking": False,
            },
        },
        timeout=180,
    )
    text_only = msg_content(body)
    print(f"  HTTP {status}, response={text_only!r}")
    if status == 200:
        try:
            parsed = parse_json_loose(text_only)
            if parsed.get("vendor") and parsed.get("total") is not None:
                passed.append("text-only kwargs extract")
            else:
                warnings.append(f"text-only extract weak parse: {parsed}")
        except Exception:
            failures.append("text-only kwargs did not return JSON")
    else:
        failures.append(f"text-only extract HTTP {status}")

    print("\n[8] Multi-image (2 pages, OpenAI content format)")
    if vision:
        content: list[dict] = []
        for index, color in enumerate(("white", "lightgray")):
            content.append({"type": "text", "text": f"Page {index + 1}"})
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{jpeg_b64(color=color)}"},
                }
            )
        status, body = post_json(
            base,
            "/chat/completions",
            {
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 64,
                "temperature": 0.2,
                "chat_template_kwargs": {
                    "template": json.dumps({"page_count": "number"}),
                    "instructions": "Return page_count as number of document pages shown.",
                    "enable_thinking": False,
                },
            },
            timeout=300,
        )
        multi_text = msg_content(body)
        print(f"  HTTP {status}, response={multi_text[:200]!r}")
        if status != 200:
            err = (body.get("error") or {}).get("message", body)
            failures.append(f"multi-image HTTP {status}: {err}")
        else:
            passed.append("multi-image request accepted")
    else:
        print("  SKIPPED (vision off)")
        warnings.append("multi-image not tested — vision off")

    print("\n[9] markdown mode kwargs (Repody markdown path)")
    if vision:
        status, body = post_json(
            base,
            "/chat/completions",
            {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
                        ],
                    }
                ],
                "max_tokens": 128,
                "temperature": 0.2,
                "chat_template_kwargs": {
                    "mode": "markdown",
                    "enable_thinking": False,
                },
            },
            timeout=300,
        )
        markdown_text = msg_content(body)
        print(f"  HTTP {status}, len={len(markdown_text)}, preview={markdown_text[:120]!r}")
        if status == 200 and markdown_text:
            passed.append("markdown mode")
        elif status != 200:
            failures.append(f"markdown mode HTTP {status}")
        else:
            warnings.append("markdown mode returned empty content")
    else:
        print("  SKIPPED (vision off)")

    print("\n" + "=" * 60)
    print(f"PASSED ({len(passed)}):")
    for item in passed:
        print("  +", item)
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for item in warnings:
            print("  !", item)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for item in failures:
            print("  -", item)
        print("\nOVERALL: NOT READY FOR REPODY")
        print("AUDIT_VLLM_SERVED_MODEL=" + model)
        return 1

    print("\nOVERALL: READY FOR REPODY")
    print("Suggested .env:")
    print("  AUDIT_VLLM_BASE_URL=http://host.docker.internal:5005/v1")
    print("  AUDIT_VLLM_SERVED_MODEL=" + model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
