export type NuExtractTypeGroup = "common" | "advanced";

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

const ALL_TYPE_VALUES = new Set<string>(NUEXTRACT_TEMPLATE_TYPE_DEFS.map((t) => t.value));

export function isNuExtractTemplateType(value: string): value is NuExtractTemplateType {
  return ALL_TYPE_VALUES.has(value);
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
    advanced: [],
  };
  for (const value of types) {
    grouped[getTemplateTypeGroup(value)].push(value);
  }
  return grouped;
}
