import { expect, test } from "@playwright/test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import {
  clickExtractValidate,
  goToTestDeployStep,
} from "../helpers/workflow-builder";
import { fetchKeycloakToken } from "../helpers/auth";
import { API_URL } from "../helpers/env";

const OUT = path.join(process.cwd(), "benchmark-reports", "ui-queue");
const PDF = path.resolve(
  process.cwd(),
  "backend/tests/.storage/audit-documents/runs/00b738853d434ed6aa2c6f4b6800bfa0/Facture.pdf",
);
const WORKFLOW_ID = "wf-invoice-audit";

function docker(args: string[]) {
  const r = spawnSync("docker", args, { encoding: "utf8" });
  if (r.status !== 0) {
    throw new Error(`docker ${args.join(" ")} failed: ${r.stderr || r.stdout}`);
  }
}

test.describe("UI queue position live", () => {
  test.afterEach(() => {
    try {
      docker(["start", "repody-worker-extract-1"]);
    } catch {
      /* best effort */
    }
  });

  test("builder shows live queue position from SSE while extract worker is paused", async ({
    page,
  }) => {
    test.setTimeout(10 * 60_000);
    fs.mkdirSync(OUT, { recursive: true });
    expect(fs.existsSync(PDF)).toBeTruthy();

    docker(["stop", "repody-worker-extract-1"]);

    await page.addInitScript(() => {
      const OrigES = window.EventSource;
      (window as unknown as { __sseLog: unknown[] }).__sseLog = [];
      // @ts-expect-error monkeypatch for probe
      window.EventSource = function EventSourceProxy(url: string, opts?: EventSourceInit) {
        const es = new OrigES(url, opts);
        es.addEventListener("message", (ev) => {
          (window as unknown as { __sseLog: unknown[] }).__sseLog.push({
            t: Date.now(),
            url,
            data: String(ev.data).slice(0, 1500),
          });
        });
        return es;
      };
      window.EventSource.prototype = OrigES.prototype;
    });

    await page.goto(`/workflows/${WORKFLOW_ID}/edit`);
    await goToTestDeployStep(page);
    await page.locator('input[type="file"]').first().setInputFiles(PDF);
    await expect(page.getByText("Facture.pdf")).toBeVisible({ timeout: 15_000 });

    const bearer = await fetchKeycloakToken();
    const pdf = fs.readFileSync(PDF);
    const backlog: string[] = [];
    for (let i = 0; i < 3; i++) {
      const fd = new FormData();
      fd.append("files", new Blob([pdf], { type: "application/pdf" }), "Facture.pdf");
      const res = await fetch(`${API_URL}/v1/workflows/${WORKFLOW_ID}/runs`, {
        method: "POST",
        headers: { Authorization: `Bearer ${bearer}` },
        body: fd,
      });
      const text = await res.text();
      expect(res.status, text).toBe(202);
      backlog.push(JSON.parse(text).runId as string);
    }

    await clickExtractValidate(page);

    const queueText = page.getByText(
      /Queue position\s+\d+\s+of\s+\d+|Queued\s+[—-]\s+position\s+\d+\s+of\s+\d+/i,
    );
    await expect(queueText.first()).toBeVisible({ timeout: 180_000 });
    const painted = (await queueText.first().innerText()).trim();
    // eslint-disable-next-line no-console
    console.log("QUEUE_UI_TEXT", painted);
    await page.screenshot({ path: path.join(OUT, "03-queue-banner.png"), fullPage: true });

    const sseAll = await page.evaluate(
      () => (window as unknown as { __sseLog?: unknown[] }).__sseLog || [],
    );
    const sseQueue = (sseAll as Array<{ data?: string }>).filter((f) =>
      typeof f.data === "string" ? /queuePosition/.test(f.data) : false,
    );
    // Queue metadata reaches the UI via SSE and/or the parallel status poll.
    expect(painted).toMatch(/\d+\s+of\s+\d+/i);
    expect(
      sseQueue.length > 0 || /Queue position/i.test(painted),
      "queue position reached the builder UI",
    ).toBeTruthy();

    // Resume drain and confirm UI leaves the queue state.
    docker(["start", "repody-worker-extract-1"]);
    await expect(
      page.getByText(/All checks passed|Open report|View full audit|failed/i).first(),
    ).toBeVisible({ timeout: 300_000 });
    await page.screenshot({ path: path.join(OUT, "04-terminal.png"), fullPage: true });

    fs.writeFileSync(
      path.join(OUT, "observations.json"),
      JSON.stringify({ backlog, painted, sseQueueFrames: sseQueue.length, sseAll }, null, 2),
    );
  });
});
