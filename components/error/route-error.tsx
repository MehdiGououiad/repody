"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { Button } from "@/components/ui/button";

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="panel-elevated rounded-xl px-6 py-10 text-center space-y-4 max-w-lg mx-auto">
      <h2 className="text-base font-semibold text-on-surface">Something went wrong</h2>
      <p className="text-sm text-on-surface-variant">
        This section failed to load. You can try again or go back to the dashboard.
      </p>
      <div className="flex items-center justify-center gap-2">
        <Button type="button" size="sm" onClick={() => reset()}>
          Try again
        </Button>
        <Button type="button" size="sm" variant="outline" asChild>
          <a href="/dashboard">Dashboard</a>
        </Button>
      </div>
    </div>
  );
}
