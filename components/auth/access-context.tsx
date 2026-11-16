"use client";

import { createContext, use } from "react";
import { MAIN_NAV_ITEMS } from "@/lib/navigation";
import type { Access, Permission } from "@/lib/types";

const NO_ACCESS: Access = { roles: [], permissions: [], withCredits: [] };

const AccessContext = createContext<Access>(NO_ACCESS);

/** What the signed-in caller may do (`GET /v1/me`), resolved once by the app shell. */
export const AccessProvider = AccessContext;

export function useAccess(): Access {
  return use(AccessContext);
}

/** Whether to offer an action. A playground visitor is also offered the paid ones: the API
 * answers 402 and the app asks them to contact us. */
export function useCan(permission: Permission): boolean {
  const { permissions, withCredits } = use(AccessContext);
  return permissions.includes(permission) || withCredits.includes(permission);
}

export function useNavItems() {
  const { permissions } = use(AccessContext);
  return MAIN_NAV_ITEMS.filter((item) => !item.permission || permissions.includes(item.permission));
}
