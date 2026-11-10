"use client";

import { createAuthClient } from "better-auth/react";

/** Better Auth in the browser: only sign-out is needed (sign-in is a server action). */
export const authClient = createAuthClient();

/** End the session and go to the login page (back to `returnTo` after signing in again). */
export async function signOutToLogin(returnTo?: string): Promise<void> {
  await authClient.signOut().catch(() => undefined);
  const login = new URL("/login", window.location.origin);
  if (returnTo) login.searchParams.set("callbackUrl", returnTo);
  window.location.assign(login);
}
