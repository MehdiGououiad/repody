"use client";

import { useEffect, useState } from "react";
import { browserApi } from "@/lib/api/openapi-client";

export type QueueLiveSnapshot = {
  queuedRuns: number;
  runningRuns: number;
  inflightRuns: number;
  lastUpdated: Date | null;
  live: boolean;
};

const REFRESH_MS = 3_000;

const EMPTY: QueueLiveSnapshot = {
  queuedRuns: 0,
  runningRuns: 0,
  inflightRuns: 0,
  lastUpdated: null,
  live: false,
};

export function useQueueLive(enabled = true): QueueLiveSnapshot {
  const [snapshot, setSnapshot] = useState<QueueLiveSnapshot>(EMPTY);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    async function refresh() {
      try {
        const { data, response } = await browserApi.GET("/v1/healthz");
        if (cancelled || !response.ok || !data) return;
        const body = data as {
          queuedRuns?: number;
          runningRuns?: number;
          inflightRuns?: number;
        };
        const queued = body.queuedRuns ?? 0;
        const running =
          body.runningRuns ??
          Math.max(0, (body.inflightRuns ?? 0) - queued);
        setSnapshot({
          queuedRuns: queued,
          runningRuns: running,
          inflightRuns: body.inflightRuns ?? queued + running,
          lastUpdated: new Date(),
          live: true,
        });
      } catch {
        if (!cancelled) {
          setSnapshot((prev) => ({ ...prev, live: false }));
        }
      }
    }

    void refresh();
    const id = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [enabled]);

  return snapshot;
}
