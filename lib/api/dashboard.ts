import type { DashboardResponse, QueueSnapshot } from "@/lib/api/schema-types";

export type { QueueSnapshot };

export type DashboardSnapshot = DashboardResponse;

export type DashboardBundle = DashboardSnapshot & {
  apiLive: boolean;
};

export const EMPTY_DASHBOARD_QUEUE: QueueSnapshot = { queuedRuns: 0, runningRuns: 0 };
