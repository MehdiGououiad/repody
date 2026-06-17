export type BackendHealth = {
  status: "ok" | "down" | "checking";
  latencyMs?: number;
};

export async function checkBackendHealth(): Promise<BackendHealth> {
  const start = Date.now();
  try {
    const res = await fetch("/api/v1/healthz", { cache: "no-store" });
    if (!res.ok) return { status: "down" };
    const body = await res.json();
    if (body.status === "ok") {
      return { status: "ok", latencyMs: Date.now() - start };
    }
    return { status: "down" };
  } catch {
    return { status: "down" };
  }
}
