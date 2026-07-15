export type NuExtractTypeGroup = "common" | "structure" | "advanced";

export interface NuExtractTypeDef {
  value: string;
  group: NuExtractTypeGroup;
  /** Hidden from the picker (still valid for stored workflows). */
  hidden?: boolean;
}

export const NUEXTRACT_TEMPLATE_TYPE_DEFS = [
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
  { value: "verbatim-string-list", group: "common", hidden: true },
  { value: "string-list", group: "common", hidden: true },
  { value: "integer-list", group: "common", hidden: true },
  { value: "number-list", group: "common", hidden: true },
  { value: "date-list", group: "common", hidden: true },
  { value: "date-time-list", group: "common", hidden: true },
  { value: "time-list", group: "common", hidden: true },
  { value: "boolean-list", group: "common", hidden: true },
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
  { value: "region:US", group: "advanced", hidden: true },
  { value: "region:FR", group: "advanced", hidden: true },
  { value: "region:IE", group: "advanced", hidden: true },
  { value: "region:GB", group: "advanced", hidden: true },
  { value: "region:IT", group: "advanced", hidden: true },
  { value: "region:ES", group: "advanced", hidden: true },
  { value: "region:DE", group: "advanced", hidden: true },
  { value: "region:PT", group: "advanced", hidden: true },
  { value: "region:CA", group: "advanced", hidden: true },
  { value: "region:MX", group: "advanced", hidden: true },
  { value: "region:BR", group: "advanced", hidden: true },
  { value: "region:AU", group: "advanced", hidden: true },
  { value: "region:JP", group: "advanced", hidden: true },
  { value: "region:KR", group: "advanced", hidden: true },
] as const satisfies readonly NuExtractTypeDef[];

type NuExtractTypeDefEntry = (typeof NUEXTRACT_TEMPLATE_TYPE_DEFS)[number];

function isHiddenTemplateTypeDef(
  def: NuExtractTypeDefEntry,
): def is NuExtractTypeDefEntry & { hidden: true } {
  return "hidden" in def && def.hidden === true;
}

export type NuExtractTemplateType = NuExtractTypeDefEntry["value"];

export const NUEXTRACT_TEMPLATE_TYPES = NUEXTRACT_TEMPLATE_TYPE_DEFS;

export const DEFAULT_NUEXTRACT_TEMPLATE_TYPE: NuExtractTemplateType = "verbatim-string";

const LIST_SUFFIX = "-list";

const SCALAR_TYPE_VALUES = new Set<string>(
  NUEXTRACT_TEMPLATE_TYPE_DEFS.filter(
    (t) => !t.value.endsWith(LIST_SUFFIX) && !isStructureTemplateType(t.value),
  ).map((t) => t.value),
);

const ALL_TYPE_VALUES = new Set<string>(NUEXTRACT_TEMPLATE_TYPE_DEFS.map((t) => t.value));

/** Strip `-list` suffix; structure types pass through unchanged. */
export function scalarTemplateType(value?: string): string {
  const raw = (value || DEFAULT_NUEXTRACT_TEMPLATE_TYPE).trim();
  if (isStructureTemplateType(raw)) return raw;
  if (raw.endsWith(LIST_SUFFIX)) return raw.slice(0, -LIST_SUFFIX.length);
  return raw;
}

/** Apply or remove NuExtract array wrapper (`type-list` → template `["type"]`). */
export function withListTemplateType(value: string | undefined, asList: boolean): string {
  const scalar = scalarTemplateType(value);
  if (isStructureTemplateType(scalar)) return scalar;
  return asList ? `${scalar}${LIST_SUFFIX}` : scalar;
}

export function supportsListTemplateType(value?: string): boolean {
  return !isStructureTemplateType(value);
}

export function isNuExtractTemplateType(value: string): value is NuExtractTemplateType {
  return ALL_TYPE_VALUES.has(value);
}

export function isStructureTemplateType(value?: string): boolean {
  const current = (value || "").trim();
  return current === "object-array" || current === "enum" || current === "multi-enum";
}

export function isListTemplateType(value?: string): boolean {
  const raw = (value || "").trim();
  if (!raw.endsWith(LIST_SUFFIX) || isStructureTemplateType(raw)) return false;
  return SCALAR_TYPE_VALUES.has(raw.slice(0, -LIST_SUFFIX.length));
}

export function getVisibleTemplateTypes(): NuExtractTemplateType[] {
  return NUEXTRACT_TEMPLATE_TYPE_DEFS.filter((t) => !isHiddenTemplateTypeDef(t)).map((t) => t.value);
}

/** Types shown in the picker: visible types plus the current value when it is hidden. */
export function getSelectableTemplateTypes(currentValue?: string): NuExtractTemplateType[] {
  const visible = getVisibleTemplateTypes();
  const current = (currentValue || "").trim();
  if (current && isNuExtractTemplateType(current) && !visible.includes(current)) {
    return [...visible, current];
  }
  return visible;
}

export function getTemplateTypeGroup(value: string): NuExtractTypeGroup {
  const def = NUEXTRACT_TEMPLATE_TYPE_DEFS.find((t) => t.value === value);
  return def?.group ?? "advanced";
}

export function groupTemplateTypes(types: NuExtractTemplateType[]): Record<NuExtractTypeGroup, NuExtractTemplateType[]> {
  const grouped: Record<NuExtractTypeGroup, NuExtractTemplateType[]> = {
    common: [],
    structure: [],
    advanced: [],
  };
  for (const value of types) {
    grouped[getTemplateTypeGroup(value)].push(value);
  }
  return grouped;
}
