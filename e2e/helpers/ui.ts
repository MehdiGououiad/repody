import fs from "node:fs";
import { type APIRequestContext, expect, type Page } from "@playwright/test";
import { API, apiAuthHeaders } from "./api";
import { SAMPLE_DOCUMENT } from "./document";

/**
 * Collects what a user would see as broken: uncaught page errors, failed React renders logged
 * to the console, and 5xx answers. Call `expectNoErrors()` at the end of a test.
 */
export function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    const text = message.text();
    if (message.type() !== "error") return;
    if (/hmr|webpack-hmr|Failed to load resource|Download the React DevTools/i.test(text)) return;
    errors.push(`console: ${text.slice(0, 300)}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`);
  });
  return {
    errors,
    expectNoErrors: () => expect(errors, errors.join("\n")).toEqual([]),
  };
}

/** Opens a page and waits until it is interactive (hydrated, first data in), so keys reach React. */
export async function open(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
}

export type TempWorkflow = { id: string; name: string; documentId: string };

const json = { "content-type": "application/json" };

/** A throwaway copy of the seeded invoice workflow (same documents and rules); remove it with `dropWorkflow`. */
export async function createWorkflow(
  request: APIRequestContext,
  name = `QA ${Date.now()}`,
): Promise<TempWorkflow> {
  const source = await request.get(`${API}/v1/workflows/wf-invoice-audit`, {
    headers: apiAuthHeaders(),
  });
  expect(source.ok(), "the seeded invoice workflow is missing").toBeTruthy();
  const { documents, rules } = await source.json();
  const created = await request.post(`${API}/v1/workflows`, {
    headers: apiAuthHeaders(json),
    data: { name, description: "Created by the QA suite", owner: "QA" },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const { id } = await created.json();
  const saved = await request.put(`${API}/v1/workflows/${id}`, {
    headers: apiAuthHeaders(json),
    data: { name, description: "Created by the QA suite", owner: "QA", documents, rules },
  });
  expect(saved.ok(), await saved.text()).toBeTruthy();
  return { id, name, documentId: documents[0].id };
}

/** Starts a test run of the workflow on the sample invoice, as the signed-in user. */
export async function startRun(request: APIRequestContext, workflow: TempWorkflow) {
  const response = await request.post(`${API}/v1/workflows/${workflow.id}/runs`, {
    headers: apiAuthHeaders(),
    multipart: {
      files: {
        name: "Facture.pdf",
        mimeType: "application/pdf",
        buffer: fs.readFileSync(SAMPLE_DOCUMENT),
      },
      documents: workflow.documentId,
    },
  });
  expect(response.status(), await response.text()).toBe(202);
  return (await response.json()).runId as string;
}

export async function dropWorkflow(request: APIRequestContext, id: string) {
  await request.delete(`${API}/v1/workflows/${id}`, { headers: apiAuthHeaders() });
}

/** The builder is a lazily loaded client component: wait for its step tabs. */
export async function openBuilder(page: Page, id: string) {
  await page.goto(`/workflows/${id}/edit`);
  await expect(page.getByRole("tab", { name: /Extraction/ })).toBeVisible({ timeout: 60_000 });
}
