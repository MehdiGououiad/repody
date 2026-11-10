import {
  defaultShouldDehydrateQuery,
  environmentManager,
  MutationCache,
  QueryClient,
} from "@tanstack/react-query";
import { apiErrorMessage } from "@/lib/api/api-error";
import { reportClientError } from "@/lib/report-error";

/** https://tanstack.com/query/latest/docs/framework/react/guides/advanced-ssr */
function makeQueryClient(): QueryClient {
  return new QueryClient({
    // Every failed write reaches error reporting (Bugsink), whichever component made it.
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) =>
        reportClientError(error, { mutation: mutation.options.mutationKey }),
    }),
    defaultOptions: {
      queries: {
        // With SSR, set a staleTime above 0 so the client does not refetch immediately.
        staleTime: 60 * 1000,
      },
      dehydrate: {
        // Include pending queries: pages start prefetches without awaiting them (streaming).
        shouldDehydrateQuery: (query) =>
          defaultShouldDehydrateQuery(query) || query.state.status === "pending",
        // Next.js detects dynamic pages by their errors; do not redact them.
        shouldRedactErrors: () => false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

/** A new client per server call (nothing shared between requests); one for the browser tab. */
export function getQueryClient(): QueryClient {
  if (environmentManager.isServer()) return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

/** The message of an error thrown by an `$api` query or mutation (the API's error body). */
export function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error) return error.message || fallback;
  return apiErrorMessage(error) || fallback;
}
