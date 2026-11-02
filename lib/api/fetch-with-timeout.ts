export type TimedRequestInit = RequestInit & { timeoutMs?: number };

/** `fetch` that aborts after `timeoutMs` (keeping the caller's signal) with a readable error. */
export async function fetchWithTimeout(
  input: string,
  { timeoutMs, ...init }: TimedRequestInit = {}
): Promise<Response> {
  if (!timeoutMs) return fetch(input, init);
  const timeout = AbortSignal.timeout(timeoutMs);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout]) : timeout;
  try {
    return await fetch(input, { ...init, signal });
  } catch (err) {
    if (timeout.aborted) {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw err;
  }
}
