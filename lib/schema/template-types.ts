/**
 * The platform's spelling of NuExtract template types. The types themselves come from the API
 * (`GET /v1/catalog`); a list of a leaf type is spelled `<type>-list` (`["number"]` in NuExtract).
 */
import type { Catalog } from "@/lib/types";

const LIST_SUFFIX = "-list";

export function isListType(value: string): boolean {
  return value.endsWith(LIST_SUFFIX) && value !== LIST_SUFFIX;
}

/** The type without its `-list` suffix. */
export function scalarType(value: string): string {
  return isListType(value) ? value.slice(0, -LIST_SUFFIX.length) : value;
}

export function withList(value: string, asList: boolean, catalog: Catalog): string {
  const scalar = scalarType(value);
  const listable = catalog.templateTypes.find((t) => t.value === scalar)?.listable ?? true;
  return asList && listable ? `${scalar}${LIST_SUFFIX}` : scalar;
}
