"use client";

import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** Pathname safe for SSR/hydration — empty until the client has mounted. */
export function useClientPathname(): string {
  const pathname = usePathname();
  return useSyncExternalStore(
    subscribe,
    () => pathname,
    () => ""
  );
}
