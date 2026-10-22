export type TimedRequestInit = RequestInit & { timeoutMs?: number };

/** `fetch` that aborts after `timeoutMs` and reports it as a readable error. */
export async function fetchWithTimeout(
  input: string,
  { timeoutMs, ...init }: TimedRequestInit = {}
): Promise<Response> {
  if (!timeoutMs) return fetch(input, init);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
