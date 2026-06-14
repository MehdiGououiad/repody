"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function useQueryParam(key: string, defaultValue = "") {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const value = searchParams.get(key) ?? defaultValue;

  const setValue = useCallback(
    (next: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (!next || next === defaultValue) {
        params.delete(key);
      } else {
        params.set(key, next);
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [defaultValue, key, pathname, router, searchParams]
  );

  return [value, setValue] as const;
}
