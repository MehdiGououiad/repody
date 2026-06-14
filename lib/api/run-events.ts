import { fetchEventSource } from "@microsoft/fetch-event-source";
import type { RunProgress } from "@/lib/api/run-poll";

export type RunEventPayload = {
  runId?: string;
  progress?: RunProgress;
  terminal?: boolean;
  status?: string;
  disabled?: boolean;
  reason?: string;
};

type WatchOptions = {
  maxMs?: number;
  headers?: HeadersInit;
};

function handleEvent(
  raw: string,
  onProgress: ((progress: RunProgress) => void) | undefined,
  finish: (outcome: "done" | "failed" | "fallback") => void
) {
  try {
    const data = JSON.parse(raw) as RunEventPayload;
    if (data.progress) onProgress?.(data.progress);
    if (data.disabled) {
      finish("fallback");
      return;
    }
    if (data.terminal) {
      finish(data.status === "failed" ? "failed" : "done");
    }
  } catch {
    /* ignore malformed frames */
  }
}

/** Subscribe to run progress via SSE. Resolves when terminal or on failure/timeout. */
export async function watchRunEvents(
  runId: string,
  onProgress?: (progress: RunProgress) => void,
  options?: WatchOptions
): Promise<"done" | "failed" | "fallback"> {
  const maxMs = options?.maxMs ?? 13 * 60_000;
  const url = `/api/runs/${runId}/events`;
  const hasCustomHeaders = Boolean(
    options?.headers && Object.keys(options.headers).length > 0
  );

  return new Promise((resolve) => {
    let settled = false;
    const finish = (outcome: "done" | "failed" | "fallback") => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(outcome);
    };

    const timer = setTimeout(() => finish("fallback"), maxMs);

    if (!hasCustomHeaders && typeof EventSource !== "undefined") {
      const es = new EventSource(url);
      es.onmessage = (event) => handleEvent(event.data, onProgress, finish);
      es.onerror = () => {
        es.close();
        finish("fallback");
      };
      return;
    }

    const controller = new AbortController();
    void fetchEventSource(url, {
      signal: controller.signal,
      headers: options?.headers as Record<string, string> | undefined,
      onmessage(ev) {
        handleEvent(ev.data, onProgress, finish);
      },
      onerror() {
        controller.abort();
        finish("fallback");
      },
    }).catch(() => finish("fallback"));
  });
}
