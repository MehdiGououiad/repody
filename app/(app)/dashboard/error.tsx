"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { DashboardOffline } from "@/components/dashboard/dashboard-offline";

/** The dashboard could not be loaded (most often: the API is down). */
export default function DashboardError({ error }: { error: Error & { digest?: string } }) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);
  return <DashboardOffline />;
}
