"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { useHydrated } from "@/lib/hooks/use-hydrated";
import en from "@/messages/en.json";
import fr from "@/messages/fr.json";

/** Replaces the root layout when it fails: no translation provider and no brand stylesheet
 * here, so the text comes straight from the message files and the colours are system ones. */
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
    <html lang={french ? "fr" : "en"} style={{ colorScheme: "light dark" }}>
      <body
        style={{
          margin: 0,
          minHeight: "100dvh",
          display: "grid",
          placeItems: "center",
          font: "14px/1.5 ui-sans-serif, system-ui, sans-serif",
          background: "Canvas",
          color: "CanvasText",
        }}
      >
        <div style={{ maxWidth: 360, padding: 24 }}>
          <h1 style={{ fontSize: 18, fontWeight: 600, margin: "0 0 6px" }}>{t.title}</h1>
          <p style={{ margin: "0 0 16px", opacity: 0.7 }}>{t.reported}</p>
          <button
            type="button"
            onClick={() => reset()}
            style={{ font: "inherit", fontWeight: 500, padding: "6px 12px", cursor: "pointer" }}
          >
            {t.retry}
          </button>
        </div>
      </body>
    </html>
  );
}
