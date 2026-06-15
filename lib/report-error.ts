import * as Sentry from "@sentry/nextjs";

export function reportClientError(
  error: unknown,
  context?: Record<string, unknown>
): void {
  if (!process.env.NEXT_PUBLIC_BUGSINK_DSN) return;
  Sentry.captureException(error, context ? { extra: context } : undefined);
}
