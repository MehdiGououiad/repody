import shared from "@/lib/shared/field-types.json";
import type { Locale } from "@/lib/site";
import { en } from "./en";
import { type Dict, fr } from "./fr";

export type { Dict };

export function dict(locale: Locale): Dict {
  return locale === "fr" ? fr : en;
}

type Named = { label: string; description: string };

/** The backend's field types, grouped and named as the product names them (synced, never retyped). */
export function fieldTypeGroups(
  locale: Locale
): { group: string; title: string; types: (Named & { value: string })[] }[] {
  const text = shared[locale] as { groups: Record<string, string>; names: Record<string, Named> };
  return Object.entries(text.groups).map(([group, title]) => ({
    group,
    title,
    types: shared.types
      .filter((t) => t.group === group)
      .map(({ value }) => ({ value, ...text.names[value] })),
  }));
}
