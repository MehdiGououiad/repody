"use client";

import { createContext, use } from "react";
import { MAIN_NAV_ITEMS } from "@/lib/navigation";
import type { Access, Permission } from "@/lib/types";

const NO_ACCESS: Access = { roles: [], permissions: [], credits: null };

const AccessContext = createContext<Access>(NO_ACCESS);

/** What the signed-in caller may do (`GET /v1/me`), resolved once by the app shell. */
export const AccessProvider = AccessContext;

/** Whether the caller may do it (the API checks again). */
export function useCan(permission: Permission): boolean {
  return use(AccessContext).permissions.includes(permission);
}

export function useNavItems() {
  const { permissions } = use(AccessContext);
  return MAIN_NAV_ITEMS.filter((item) => !item.permission || permissions.includes(item.permission));
}
