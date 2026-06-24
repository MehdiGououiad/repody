"""Extract e2e/fixtures/documents/Facture.pdf via Repody VLM and report timing."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import urllib.request
from pathlib import Path

from audit_workbench.extraction.base import SchemaFieldSpec
from audit_workbench.extraction.document_bundle import DocumentBundle
from audit_workbench.extraction.repody_vlm import _vlm_pages, extract_with_repody_vlm
from audit_workbench.settings import get_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = REPO_ROOT / "e2e" / "fixtures" / "documents" / "Facture.pdf"
EXPECTED = {"total_amount": "6000.00", "tva": "1000.00"}


def wait_server(host: str, *, timeout: float = 180.0) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        try:
            with urllib.request.urlopen(f"{host.rstrip('/')}/health", timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def values_match(actual: str, expected: str) -> bool:
    norm = str(actual).replace(",", ".").strip()
    if norm == expected:
        return True
    try:
        return abs(float(norm) - float(expected)) < 0.01
    except ValueError:
        return False


async def run(pdf: Path, host: str) -> int:
    get_settings.cache_clear()

    if not wait_server(host):
        print(f"ERROR: server not reachable at {host}")
        return 2

    schema = [
        SchemaFieldSpec(name="total_amount", description="Total TTC including tax"),
        SchemaFieldSpec(name="tva", description="Total TVA tax amount"),
    ]
    raw = pdf.read_bytes()
    bundle = DocumentBundle(raw_bytes=raw, mime_type="application/pdf")
    settings = get_settings()

    started = time.perf_counter()
    pages, page_count = _vlm_pages(bundle, settings)
    render_s = time.perf_counter() - started

    infer_started = time.perf_counter()
    try:
        result = await extract_with_repody_vlm(
            bundle,
            schema,
            "Invoice",
            extraction_instructions="French invoice fixture.",
        )
    except Exception as exc:
        infer_s = time.perf_counter() - infer_started
        print(f"Extraction failed after {infer_s:.2f}s: {exc!r}")
        return 1
    infer_s = time.perf_counter() - infer_started
    total_s = time.perf_counter() - started

    fields = {field.key: field.value for field in result.fields}
    page_bytes = len(pages[0][0]) if pages else 0

    print("=== Facture.pdf inference test ===")
    print(f"Fixture: {pdf}")
    print(f"Server:  {settings.vllm_base_url}")
    print(f"Model:   {settings.vllm_served_model}")
    print(f"Pages:   {page_count} ({page_bytes:,} byte PNG)")
    print()
    print("TIMING")
    print(f"  PDF render:   {render_s * 1000:7.0f} ms  ({render_s:.3f} s)")
    print(f"  VLM request:  {infer_s * 1000:7.0f} ms  ({infer_s:.3f} s)")
    print(f"  End-to-end:   {total_s * 1000:7.0f} ms  ({total_s:.3f} s)")
    print()
    print("FIELDS (benchmark: total_amount=6000.00, tva=1000.00)")
    all_ok = True
    for name in ("total_amount", "tva"):
        value = fields.get(name, "")
        expected = EXPECTED[name]
        ok = values_match(value or "", expected)
        all_ok = all_ok and ok
        status = "PASS" if ok else "MISS"
        print(f"  {name}: {value!r}  {status} (expected {expected})")
    print()
    print("raw JSON:", result.raw_text)

    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--host", default="http://127.0.0.1:5005")
    args = parser.parse_args()
    return asyncio.run(run(args.pdf, args.host))


if __name__ == "__main__":
    sys.exit(main())
