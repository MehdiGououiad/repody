import { browserApi } from "@/lib/api/openapi-client";

export type BackendHealth = {
  status: "ok" | "down" | "checking";
  latencyMs?: number;
};

export async function checkBackendHealth(): Promise<BackendHealth> {
  const start = Date.now();
  try {
    // Liveness only — badge should not ping Redis/DB/queues every 30s.
    const { data, response } = await browserApi.GET("/v1/healthz/live");
    if (!response.ok || data?.status !== "ok") return { status: "down" };
    return { status: "ok", latencyMs: Date.now() - start };
  } catch {
    return { status: "down" };
  }
}
