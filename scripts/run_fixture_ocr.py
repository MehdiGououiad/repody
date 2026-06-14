#!/usr/bin/env python3
"""Upload a fixture PDF and poll until the test run completes."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "http://localhost:8000/v1"
WORKFLOW_ID = "wf-invoice-audit"
DOC_ID = "doc-invoice"
POLL_SECONDS = 3
MAX_WAIT_SECONDS = 600


def main() -> int:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("e2e/fixtures/documents/Facture.pdf")
    if not pdf.is_file():
        print(f"File not found: {pdf}", file=sys.stderr)
        return 1

    import mimetypes

    try:
        import httpx
    except ImportError:
        print("Install httpx: pip install httpx", file=sys.stderr)
        return 1

    with httpx.Client(timeout=120.0) as client:
        with pdf.open("rb") as fh:
            res = client.post(
                f"{API}/workflows/{WORKFLOW_ID}/runs",
                params={"mode": "test"},
                data={"document_ids": json.dumps([DOC_ID])},
                files={"files": (pdf.name, fh, mimetypes.guess_type(pdf.name)[0] or "application/pdf")},
            )
        res.raise_for_status()
        run_id = res.json()["runId"]
        print(f"Started run: {run_id}")

        deadline = time.time() + MAX_WAIT_SECONDS
        while time.time() < deadline:
            poll = client.get(f"{API}/runs/{run_id}").json()
            status = poll.get("status")
            progress = poll.get("progress") or {}
            label = progress.get("label", "")
            print(f"  {status}: {label}")
            if status == "done":
                print(json.dumps(poll.get("result"), indent=2, ensure_ascii=False))
                return 0
            if status == "failed":
                print("FAILED:", poll.get("error"), file=sys.stderr)
                return 2
            time.sleep(POLL_SECONDS)

    print("Timed out waiting for run", file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
