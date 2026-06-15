"use client";

import { HealthStrip } from "@/components/dashboard/health-strip";
import type { HealthAlert } from "@/lib/types";

export function DashboardAlerts({ alerts }: { alerts: HealthAlert[] }) {
  if (!alerts.length) return null;
  return <HealthStrip alerts={alerts} />;
}
