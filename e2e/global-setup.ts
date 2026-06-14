import type { FullConfig } from "@playwright/test";

async function waitForOk(url: string, label: string, attempts = 60): Promise<void> {
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
      if (res.ok) {
        console.log(`[e2e] ${label} ready at ${url}`);
        return;
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`[e2e] Timed out waiting for ${label} at ${url}`);
}

export default async function globalSetup(config: FullConfig) {
  const apiURL = (config.metadata?.apiURL as string) ?? "http://localhost:8000";
  const webURL = process.env.E2E_WEB_URL ?? "http://localhost:3000";

  await waitForOk(`${apiURL}/v1/healthz`, "API");
  await waitForOk(webURL, "Web");
}
