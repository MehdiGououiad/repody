import type { Dashboard } from "@/lib/types";

/** Runs of the last 7 days that need a person: rejected or flagged for a check. */
export function reviewCount(series: Dashboard["performanceSeries"]): number {
  return series.slice(-7).reduce((sum, day) => sum + day.warning + day.failed, 0);
}
