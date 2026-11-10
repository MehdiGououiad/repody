"use client";

import { $api } from "@/lib/api/browser";
import type { Catalog } from "@/lib/types";

/** The builder's field-type catalog from the API (it never changes while the app runs). */
export function useCatalog(): Catalog | undefined {
  return $api.useQuery("get", "/v1/catalog", undefined, { staleTime: Number.POSITIVE_INFINITY })
    .data;
}
