import { expect, test } from "@playwright/test";

const API = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("UI wiring", () => {
  test("proxy API, dashboard endpoint, and header actions work", async ({ page }) => {
    const serverErrors: string[] = [];
    page.on("response", (response) => {
      if (response.status() >= 500) {
        serverErrors.push(`${response.status()} ${response.url()}`);
      }
    });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

    const configStatus = await page.evaluate(async () => {
      const response = await fetch("/api/platform/config");
      return response.status;
    });
    expect(configStatus).toBe(200);

    await page.getByRole("button", { name: "Notifications" }).click();
    await expect(page.locator("[data-sonner-toast]")).toContainText("Coming soon");
    expect(serverErrors).toEqual([]);
  });

  test("deployed API examples match the multipart contract", async ({ page, request }) => {
    const created = await request.post(`${API}/v1/workflows`, {
      data: {
        name: `UI Wiring ${Date.now()}`,
        description: "Temporary deployed workflow for browser contract checks",
        owner: "E2E",
      },
    });
    expect(created.ok()).toBeTruthy();
    const body = (await created.json()) as {
      workflow: {
        id: string;
        documents: Array<{
          id: string;
          documentType: string;
          schema: Array<{ id: string; name: string; description: string }>;
        }>;
        [key: string]: unknown;
      };
    };
    const workflowId = body.workflow.id;

    try {
      body.workflow.documents[0].documentType = "Invoice";
      body.workflow.documents[0].schema = [
        {
          id: `field-${Date.now()}`,
          name: "invoice_number",
          description: "Invoice identifier",
        },
      ];
      const configured = await request.put(`${API}/v1/workflows/${workflowId}`, {
        data: body.workflow,
      });
      expect(configured.ok()).toBeTruthy();

      const deployed = await request.post(`${API}/v1/workflows/${workflowId}/deploy`);
      expect(deployed.ok()).toBeTruthy();

      await page.goto(`/workflows/${workflowId}/edit`);
      await page.getByRole("button", { name: /Test & Deploy/i }).click();
      await page.getByRole("tab", { name: /Deploy & API/i }).click();

      await expect(
        page.locator("code").filter({
          hasText: `/api/v1/workflows/${workflowId}/runs`,
        }).first()
      ).toBeVisible();
      await expect(page.getByText(/-F "files=@\/path\/to\/document\.pdf"/)).toBeVisible();

      await page.getByRole("tab", { name: "python" }).click();
      await expect(page.getByText(/files=\{"files": document\}/)).toBeVisible();

      await page.getByRole("tab", { name: "js" }).click();
      await expect(page.getByText(/form\.append\("files", file\)/)).toBeVisible();
    } finally {
      await request.delete(`${API}/v1/workflows/${workflowId}`);
    }
  });

  test("audit list CSV export downloads a report", async ({ page }) => {
    await page.goto("/audits");
    await expect(page.getByText("AUD-2023-8902")).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: /Export CSV/i }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/^audit-runs-\d{4}-\d{2}-\d{2}\.csv$/);
  });
});
