"use client";

import { createContext, use } from "react";
import type { Account } from "@/lib/auth/account";

const AccountContext = createContext<Promise<Account | null>>(Promise.resolve(null));

/** The signed-in account, resolved on the server (null without Keycloak); a promise, so the
 * shell renders before it is known. https://nextjs.org/docs/app/guides/authentication */
export const AccountProvider = AccountContext;

/** Suspends until the account is known: call it inside a `<Suspense>` boundary. */
export function useAccount(): Account | null {
  return use(use(AccountContext));
}
