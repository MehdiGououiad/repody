import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";
import { accessToken, oidcEnabled } from "@/lib/auth/server";

/**
 * The Data Access Layer's session check (Next.js authentication guide): every server-side read
 * of the API calls it, so access is checked next to the data, not only by the proxy. Returns the
 * session's Keycloak token (null when sign-in is off); without a session, goes to the login page.
 * Memoized for one render pass.
 */
export const verifySession = cache(async (): Promise<string | null> => {
  if (!oidcEnabled) return null;
  const token = await accessToken(await headers());
  if (!token) redirect("/login");
  return token.token;
});
