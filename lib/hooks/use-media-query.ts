"use client";

import { useSyncExternalStore } from "react";

/** Whether a media query matches, kept in sync; the server renders the wide layout. */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => true
  );
}
