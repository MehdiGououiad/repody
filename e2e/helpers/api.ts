const API = process.env.E2E_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API}/v1${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown, headers?: HeadersInit): Promise<T> {
  const res = await fetch(`${API}/v1${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function pollRun(
  runId: string,
  maxAttempts = 30,
  intervalMs = 500
): Promise<{ status: string; result?: unknown; error?: string }> {
  for (let i = 0; i < maxAttempts; i++) {
    const body = await apiGet<{ status: string; result?: unknown; error?: string }>(
      `/runs/${runId}`
    );
    if (body.status === "done" || body.status === "failed") return body;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Run ${runId} did not complete in time`);
}

export { API };
