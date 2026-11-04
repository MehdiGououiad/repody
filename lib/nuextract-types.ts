export type NuExtractTypeGroup = "common" | "structure" | "advanced";

/** NuExtract template types offered in the schema picker. Stored workflows may use others
 * (e.g. `region:FR`); the picker then shows the stored value as is. */
const TEMPLATE_TYPE_DEFS = [
  { value: "verbatim-string", group: "common" },
  { value: "string", group: "common" },
  { value: "integer", group: "common" },
  { value: "number", group: "common" },
  { value: "date", group: "common" },
  { value: "time", group: "common" },
  { value: "date-time", group: "common" },
  { value: "boolean", group: "common" },
  { value: "currency", group: "common" },
  { value: "email-address", group: "common" },
  { value: "phone-number", group: "common" },
  { value: "object", group: "structure" },
  { value: "object-array", group: "structure" },
  { value: "enum", group: "structure" },
  { value: "multi-enum", group: "structure" },
  { value: "duration", group: "advanced" },
  { value: "country", group: "advanced" },
  { value: "language", group: "advanced" },
  { value: "language-tag", group: "advanced" },
  { value: "script", group: "advanced" },
  { value: "url", group: "advanced" },
  { value: "iban", group: "advanced" },
  { value: "bic", group: "advanced" },
  { value: "unit-code", group: "advanced" },
] as const satisfies readonly { value: string; group: NuExtractTypeGroup }[];

const TEMPLATE_TYPES: string[] = TEMPLATE_TYPE_DEFS.map((t) => t.value);
const STRUCTURE_TYPES = new Set(["object", "object-array", "enum", "multi-enum"]);
const LIST_SUFFIX = "-list";

export const DEFAULT_NUEXTRACT_TEMPLATE_TYPE = "verbatim-string";

export function isStructureTemplateType(value?: string): boolean {
  return STRUCTURE_TYPES.has((value || "").trim());
}

/** Platform spelling of an official `["type"]` list: `type-list`. */
export function isListTemplateType(value?: string): boolean {
  const raw = (value || "").trim();
  return raw.endsWith(LIST_SUFFIX) && raw !== LIST_SUFFIX && !isStructureTemplateType(raw);
}

/** The type without its `-list` suffix. */
export function scalarTemplateType(value?: string): string {
  const raw = (value || DEFAULT_NUEXTRACT_TEMPLATE_TYPE).trim();
  return isListTemplateType(raw) ? raw.slice(0, -LIST_SUFFIX.length) : raw;
}

export function withListTemplateType(value: string | undefined, asList: boolean): string {
  const scalar = scalarTemplateType(value);
  return asList && !isStructureTemplateType(scalar) ? `${scalar}${LIST_SUFFIX}` : scalar;
}

/** Picker types by group, plus the current value when it is not one of them. */
export function groupedTemplateTypes(currentValue?: string): Record<NuExtractTypeGroup, string[]> {
  const grouped: Record<NuExtractTypeGroup, string[]> = { common: [], structure: [], advanced: [] };
  for (const def of TEMPLATE_TYPE_DEFS) grouped[def.group].push(def.value);
  const current = scalarTemplateType(currentValue);
  if (!TEMPLATE_TYPES.includes(current)) grouped.advanced.push(current);
  return grouped;
}
