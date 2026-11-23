# ruff: noqa: T201 - a script: it reports on stdout
"""Production smoke test: one real run, end to end, as the repody-tester service account.

Runs inside the API container (the API, Postgres, storage, the Hatchet worker and the GPU it
uses are the real ones), from the stack's directory on the server:

    export TESTER_CLIENT_SECRET=$(grep '^TESTER_CLIENT_SECRET=' .env | cut -d= -f2-)
    docker compose --env-file .env --env-file release.env exec -T -e TESTER_CLIENT_SECRET \\
      api python - < tools/smoke_test.py

It signs in with client credentials (deploy/keycloak/setup-tester-client.sh), tops up its own
company's credits when low, saves a one-document workflow, runs a generated one-page invoice
through extraction, and checks the report, the credits charged and that the account reaches
nothing outside its company. Each run costs a few credits and a little GPU time (Modal). It
prints one line per check and exits 1 on the first failure.
"""

import asyncio
import io
import os
import sys
import time

import httpx
from PIL import Image, ImageDraw

from repody.app import credits
from repody.infra import db
from repody.settings import get_settings

API = "http://127.0.0.1:8000/v1"
ACCOUNT = "client-repody-test"
WORKFLOW = "wf-smoke-test"
TOP_UP_BELOW, TOP_UP = 30, 100
RUN_TIMEOUT_SECONDS = 15 * 60
DEFINITION = {
    "name": "Smoke test (automatic)",
    "documents": [
        {
            "id": "doc-invoice",
            "documentType": "Invoice",
            "schema": [
                {"id": "f-number", "name": "invoice_number", "templateType": "verbatim-string"},
                {"id": "f-total", "name": "total_amount", "templateType": "number"},
            ],
        }
    ],
    "rules": [],
}


def check(ok: bool, what: str) -> None:
    print(("ok    " if ok else "FAIL  ") + what, flush=True)
    if not ok:
        sys.exit(1)


class TesterAuth(httpx.Auth):
    """Client credentials, signing in again when a token expires (Keycloak's last 5 minutes, and
    a cold GPU start can take longer)."""

    def __init__(self) -> None:
        self.value = token()

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self.value}"
        response = yield request
        if response.status_code == 401:
            self.value = token()
            request.headers["Authorization"] = f"Bearer {self.value}"
            yield request


def token() -> str:
    issuer = (
        get_settings().keycloak_internal_issuer or "http://keycloak:8080/realms/repody"
    ).rstrip("/")
    response = httpx.post(
        f"{issuer}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "repody-tester",
            "client_secret": os.environ["TESTER_CLIENT_SECRET"],
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def invoice_png() -> bytes:
    page = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(page)
    for y, line in enumerate(
        [
            "ACME SARL",
            "INVOICE",
            "Invoice number: SMOKE-0042",
            "Date: 2026-11-17",
            "",
            "Total: 1250.00 EUR",
        ]
    ):
        draw.text((120, 140 + y * 60), line, fill="black")
    buffer = io.BytesIO()
    page.save(buffer, format="PNG")
    return buffer.getvalue()


async def top_up() -> None:
    async with db.session_factory() as session:
        available, _held = await credits.balances(session, ACCOUNT)
        if available < TOP_UP_BELOW:
            await credits.grant(session, ACCOUNT, TOP_UP, "smoke test top-up", "smoke-test")
            await session.commit()
            print(f"      topped up {ACCOUNT}: +{TOP_UP} credits", flush=True)


def main() -> None:
    started = time.monotonic()
    api = httpx.Client(base_url=API, auth=TesterAuth(), timeout=60)
    me = api.get("/me").json()
    check(me.get("credits", {}).get("account") == ACCOUNT, f"signed in as {ACCOUNT}")
    check(
        "run:execute" in me["permissions"] and "clients:manage" not in me["permissions"],
        "operator, not admin",
    )

    asyncio.run(top_up())
    before = api.get("/me").json()["credits"]["balance"]

    check(api.put(f"/workflows/{WORKFLOW}", json=DEFINITION).status_code == 200, "workflow saved")
    started_run = api.post(
        f"/workflows/{WORKFLOW}/runs", files={"files": ("invoice.png", invoice_png(), "image/png")}
    )
    check(started_run.status_code == 202, f"run queued ({started_run.status_code})")
    run_id = started_run.json()["runId"]

    deadline = time.monotonic() + RUN_TIMEOUT_SECONDS
    while True:
        polled = api.get(f"/runs/{run_id}")
        if polled.status_code != 200:
            check(False, f"run {run_id} readable ({polled.status_code})")
        state = polled.json()
        if state["status"] in ("done", "failed") or time.monotonic() > deadline:
            break
        time.sleep(5)
    check(
        state["status"] == "done",
        f"run {run_id} done ({state['status']}: {state.get('error') or 'no error'})",
    )
    document = state["result"]["documents"][0]
    meta = document.get("extraction") or {}
    check(not meta.get("error"), "extracted without error")
    values = {f["key"]: f["value"] for f in document["fields"]}
    print(f"      extracted {values} in {meta.get('extractionMs')} ms", flush=True)
    check(values.get("total_amount") is not None, "the model read the total")

    after = api.get("/me").json()["credits"]
    charged = before - after["balance"]
    check(charged > 0 and after["held"] == 0, f"charged {charged} credits, nothing left held")

    # The account may have run other workflows of its own (load or accuracy tests): what it must
    # never see is a run of a workflow it cannot open, which would be another company's.
    audits = api.get("/audits", params={"limit": 200}).json()["audits"]
    visible = {w["id"] for w in api.get("/workflows").json()["workflows"]}
    check(any(a["id"] == run_id for a in audits), "its run is in its audits")
    check(all(a["workflowId"] in visible for a in audits), "its audits are its own company's only")
    check(api.get("/admin").status_code == 403, "the admin area is refused")
    check(api.get("/audits/run-not-its-own").status_code == 404, "an unknown run is not found")
    print(f"smoke test passed in {round(time.monotonic() - started)} s", flush=True)


main()
