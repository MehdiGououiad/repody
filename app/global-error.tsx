"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
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
    <html lang="en">
      <body className="min-h-screen flex items-center justify-center p-6 bg-surface text-on-surface">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="text-sm text-on-surface-variant">
            The error was reported. You can try again or refresh the page.
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
