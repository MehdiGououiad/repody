/**
 * Import / export NuExtract JSON templates ↔ workflow SchemaField rows.
 *
 * Official constructors (NuExtract3):
 * - leaf type strings (TYPES.md)
 * - nested objects `{ ... }`
 * - lists `["type"]`
 * - enums `["a", "b", …]` (≥2 choices)
 * - multi-enums `[["A", "B", …]]`
 * - object arrays `[{ ... }]` (one prototype object)
 *
 * @see https://huggingface.co/numind/NuExtract3
 * @see https://huggingface.co/numind/NuExtract3/blob/main/TYPES.md
 */

import {
  DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
  isStructureTemplateType,
  type NuExtractTemplateType,
  withListTemplateType,
} from "@/lib/nuextract-types";
import type { SchemaField } from "@/lib/types";
import { shortId } from "@/lib/utils";

export type ImportNuextractTemplateResult =
  | { ok: true; fields: SchemaField[] }
  | { ok: false; error: "invalid_json" | "not_object" | "empty" };

/** HF prose aliases → TYPES.md names. */
const TYPE_ALIASES: Record<string, string> = {
  email: "email-address",
  phone: "phone-number",
  tel: "phone-number",
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function newField(partial: Omit<SchemaField, "id"> & { id?: string }): SchemaField {
  return {
    id: partial.id ?? `f${shortId()}`,
    name: partial.name,
    description: partial.description ?? "",
    templateType: partial.templateType,
    enumValues: partial.enumValues,
    children: partial.children,
  };
}

function leafType(raw: string): string {
  const value = raw.trim();
  if (!value) return DEFAULT_NUEXTRACT_TEMPLATE_TYPE;
  return TYPE_ALIASES[value] ?? value;
}

function fieldsFromObject(obj: Record<string, unknown>): SchemaField[] {
  const fields: SchemaField[] = [];
  for (const [name, value] of Object.entries(obj)) {
    const key = name.trim();
    if (!key) continue;
    fields.push(fieldFromNode(key, value));
  }
  return fields;
}

function fieldFromNode(name: string, value: unknown): SchemaField {
  if (typeof value === "string") {
    return newField({ name, description: "", templateType: leafType(value) });
  }

  if (isPlainObject(value)) {
    return newField({
      name,
      description: "",
      templateType: "object",
      children: fieldsFromObject(value),
    });
  }

  if (Array.isArray(value)) {
    return fieldFromArrayNode(name, value);
  }

  return newField({
    name,
    description: "",
    templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
  });
}

function fieldFromArrayNode(name: string, value: unknown[]): SchemaField {
  // Official: object-array schema is a one-element list of a prototype object.
  if (value.length > 0 && value.every((item) => isPlainObject(item))) {
    const objectProto = value[0] as Record<string, unknown>;
    return newField({
      name,
      description: "",
      templateType: "object-array",
      children: fieldsFromObject(objectProto),
    });
  }

  // Official multi-enum: [["A", "B", "C"]] with ≥2 choices preferred.
  if (
    value.length === 1 &&
    Array.isArray(value[0]) &&
    (value[0] as unknown[]).every((item) => typeof item === "string")
  ) {
    const enumValues = (value[0] as string[]).map((item) => item.trim()).filter(Boolean);
    return newField({
      name,
      description: "",
      templateType: "multi-enum",
      enumValues,
    });
  }

  // Official list: ["string"] — single type string in an array.
  if (value.length === 1 && typeof value[0] === "string") {
    const scalar = leafType(value[0]);
    if (!isStructureTemplateType(scalar)) {
      return newField({
        name,
        description: "",
        templateType: withListTemplateType(scalar as NuExtractTemplateType, true),
      });
    }
  }

  // Official enum: ["yes", "no", …] — ≥2 choice strings.
  if (value.length >= 2 && value.every((item) => typeof item === "string")) {
    const strings = value.map((item) => String(item).trim()).filter(Boolean);
    return newField({
      name,
      description: "",
      templateType: "enum",
      enumValues: strings,
    });
  }

  return newField({
    name,
    description: "",
    templateType: DEFAULT_NUEXTRACT_TEMPLATE_TYPE,
  });
}

/** Parse pasted NuExtract template JSON into schema fields. */
export function importNuextractTemplate(raw: string): ImportNuextractTemplateResult {
  const text = raw.trim();
  if (!text) return { ok: false, error: "empty" };

  let parsed: unknown;
  try {
    parsed = JSON.parse(text) as unknown;
  } catch {
    return { ok: false, error: "invalid_json" };
  }

  if (!isPlainObject(parsed)) {
    return { ok: false, error: "not_object" };
  }

  const fields = fieldsFromObject(parsed);
  if (fields.length === 0) return { ok: false, error: "empty" };
  return { ok: true, fields };
}
