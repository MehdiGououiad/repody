import { spawnSync } from "node:child_process";
import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { fetchKeycloakToken } from "../helpers/auth";
import { SAMPLE_DOCUMENT } from "../helpers/document";
import { API_URL } from "../helpers/env";
import { clickExtractValidate, goToTestDeployStep } from "../helpers/workflow-builder";

const WORKFLOW_ID = "wf-invoice-audit";
const WORKER = "repody-worker-1";

function docker(...args: string[]) {
  const result = spawnSync("docker", args, { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`docker ${args.join(" ")} failed: ${result.stderr || result.stdout}`);
  }
}

/** Start runs with the user's token so the test run waits behind them. */
async function queueRuns(count: number) {
  const bearer = await fetchKeycloakToken();
  const pdf = fs.readFileSync(SAMPLE_DOCUMENT);
  for (let i = 0; i < count; i++) {
    const form = new FormData();
    form.append("files", new Blob([pdf], { type: "application/pdf" }), "Facture.pdf");
    const response = await fetch(`${API_URL}/v1/workflows/${WORKFLOW_ID}/runs`, {
      method: "POST",
      headers: { Authorization: `Bearer ${bearer}` },
      body: form,
    });
    expect(response.status, await response.text()).toBe(202);
  }
}

test.describe("UI queue position live", () => {
  test.afterEach(() => docker("start", WORKER));

  test("builder shows the live queue position, then the result once a worker runs", async ({
    page,
  }) => {
    test.setTimeout(10 * 60_000);
    docker("stop", WORKER);

    await page.goto(`/workflows/${WORKFLOW_ID}/edit`);
    await goToTestDeployStep(page);
    await page.locator('input[type="file"]').first().setInputFiles(SAMPLE_DOCUMENT);
    await expect(page.getByText("Facture.pdf")).toBeVisible({ timeout: 15_000 });

    await queueRuns(3);
    await clickExtractValidate(page);

    // At least three runs are ahead of the test run while no worker is up.
    await expect(page.getByText(/Queue position\s+\d+\s+of\s+\d+/i).first()).toBeVisible({
      timeout: 180_000,
    });

    docker("start", WORKER);
    await expect(
      page.getByText(/All checks passed|Open report|View full audit|failed/i).first()
    ).toBeVisible({ timeout: 300_000 });
  });
});
