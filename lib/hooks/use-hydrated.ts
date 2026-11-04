"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** False during server render and hydration, true once the client has mounted. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  );
}

/** The pathname once hydrated; empty before, so server and client markup match. */
export function useClientPathname(): string {
  const pathname = usePathname();
  return useHydrated() ? pathname : "";
}
