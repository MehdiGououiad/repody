/**
 * Import a NuExtract JSON template as workflow schema fields (the API builds the template back
 * from them: `repody/extraction/nuextract.py`).
 *
 * NuExtract3 constructors: leaf type strings, nested objects `{…}`, lists `["type"]`, enums
 * `["a", "b", …]` (≥2 choices), multi-enums `[["A", "B", …]]`, object arrays `[{…}]`.
 *
 * @see https://huggingface.co/numind/NuExtract3/blob/main/TYPES.md
 */

import { withList } from "@/lib/schema/template-types";
import type { Catalog, SchemaField } from "@/lib/types";
import { DEFAULT_TEMPLATE_TYPE, newSchemaField } from "@/lib/workflow/new-items";

export type ImportNuextractTemplateResult =
  | { ok: true; fields: SchemaField[] }
  | { ok: false; error: "invalid_json" | "not_object" | "empty" };

/** Prose aliases used on the model card -> TYPES.md names. */
const TYPE_ALIASES: Record<string, string> = {
  email: "email-address",
  phone: "phone-number",
  tel: "phone-number",
};
const PARAMETERISED = /^[a-z][a-z-]*:[A-Za-z0-9_-]+$/;

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const isStrings = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === "string");
const choices = (values: string[]) => values.map((v) => v.trim()).filter(Boolean);

export function importNuextractTemplate(
  raw: string,
  catalog: Catalog,
): ImportNuextractTemplateResult {
  /** A leaf type the API accepts; anything else falls back to the default type. */
  const leaf = (value: string): string => {
    const type = TYPE_ALIASES[value.trim()] ?? value.trim();
    const known = catalog.templateTypes.some((t) => t.value === type && t.group !== "structure");
    return known || PARAMETERISED.test(type) ? type : DEFAULT_TEMPLATE_TYPE;
  };

  const fieldsOf = (object: Record<string, unknown>): SchemaField[] =>
    Object.entries(object)
      .filter(([name]) => name.trim())
      .map(([name, node]) => fieldOf(name.trim(), node));

  const fieldOf = (name: string, node: unknown): SchemaField => {
    if (typeof node === "string") return newSchemaField({ name, templateType: leaf(node) });
    if (isObject(node)) {
      return newSchemaField({ name, templateType: "object", children: fieldsOf(node) });
    }
    if (Array.isArray(node)) {
      const [first] = node;
      if (node.length > 0 && node.every(isObject)) {
        // An object array is one prototype row.
        return newSchemaField({
          name,
          templateType: "object-array",
          children: fieldsOf(first as Record<string, unknown>),
        });
      }
      if (node.length === 1 && isStrings(first)) {
        return newSchemaField({ name, templateType: "multi-enum", enumValues: choices(first) });
      }
      if (node.length === 1 && typeof first === "string") {
        return newSchemaField({ name, templateType: withList(leaf(first), true, catalog) });
      }
      if (node.length >= 2 && isStrings(node)) {
        return newSchemaField({ name, templateType: "enum", enumValues: choices(node) });
      }
    }
    return newSchemaField({ name, templateType: DEFAULT_TEMPLATE_TYPE });
  };

  const text = raw.trim();
  if (!text) return { ok: false, error: "empty" };
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, error: "invalid_json" };
  }
  if (!isObject(parsed)) return { ok: false, error: "not_object" };
  const fields = fieldsOf(parsed);
  return fields.length ? { ok: true, fields } : { ok: false, error: "empty" };
}
