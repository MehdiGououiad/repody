/**
 * Canonical name of a field, as the backend's `field_key`: `Total  Amount` -> `total_amount`,
 * `invoice.total` -> `invoice__total`. Two names address the same field when their keys match.
 */
export function fieldKey(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, "_").replaceAll(".", "__");
}
