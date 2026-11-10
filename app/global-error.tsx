"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import en from "@/messages/en.json";
import fr from "@/messages/fr.json";

/** Replaces the root layout when it fails, so there is no translation provider here: the text
 * comes straight from the message files, in the browser's language. */
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
  const french = useHydrated() && navigator.language.toLowerCase().startsWith("fr");
  const t = (french ? fr : en).error;

  return (
    <html lang={french ? "fr" : "en"}>
      <body className="min-h-screen flex items-center justify-center p-6 bg-surface text-on-surface">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-lg font-semibold">{t.title}</h1>
          <p className="text-sm text-on-surface-variant">{t.reported}</p>
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary"
          >
            {t.retry}
          </button>
        </div>
      </body>
    </html>
  );
}
