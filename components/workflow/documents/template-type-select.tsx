"use client";

import { useMessages, useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCatalog } from "@/lib/hooks/use-catalog";
import { isListType, scalarType, withList } from "@/lib/schema/template-types";
import type { TemplateTypeGroup } from "@/lib/types";
import { cn } from "@/lib/utils";

const GROUPS: TemplateTypeGroup[] = ["common", "structure", "advanced"];

/** A type's label and description, or the type itself when it has none (e.g. `region:FR`).
 * Types come from the API catalog at runtime, so they are looked up in the messages
 * (`useMessages`) rather than as typed translation keys. */
function useTypeText() {
  const texts = new Map(Object.entries(useMessages().workflows.builder.schema.templateTypes));
  return (value: string, part: "label" | "description") =>
    texts.get(scalarType(value))?.[part] ?? (part === "label" ? value : "");
}

/** The NuExtract type of a schema field (from the API catalog); a list keeps its `-list`. */
export function TemplateTypeSelect({
  value,
  onChange,
  structures = true,
  detailed = false,
}: {
  value: string;
  onChange: (value: string) => void;
  /** Offer object, table and enum types (table columns are scalars only). */
  structures?: boolean;
  /** Show each type's description (the wide schema table). */
  detailed?: boolean;
}) {
  const t = useTranslations("workflows.builder.schema");
  const catalog = useCatalog();
  const text = useTypeText();
  const scalar = scalarType(value);
  const list = isListType(value);
  if (!catalog) return <div className="h-9 rounded-md bg-surface-container-low animate-pulse" />;

  const known = catalog.templateTypes.some((type) => type.value === scalar);
  const groups = GROUPS.filter((group) => structures || group !== "structure");

  return (
    <Select value={scalar} onValueChange={(next) => onChange(withList(next, list, catalog))}>
      <SelectTrigger
        className={cn(
          "text-xs min-w-0 w-full",
          detailed &&
            "h-auto min-h-8 py-1 border-transparent bg-transparent shadow-none focus:bg-card gap-2"
        )}
      >
        {detailed ? (
          <>
            <SelectValue className="sr-only" aria-label={text(value, "label")} />
            <span className="flex min-w-0 flex-1 flex-col items-start text-left overflow-hidden">
              <span className="w-full truncate font-medium leading-tight">
                {text(value, "label")}
              </span>
              <span className="w-full truncate text-[10px] text-on-surface-variant leading-tight">
                {text(value, "description")}
                {list ? ` · ${t("listModeSuffix")}` : ""}
              </span>
            </span>
          </>
        ) : (
          <SelectValue />
        )}
      </SelectTrigger>
      <SelectContent className="max-h-80 w-72">
        {groups.map((group) => (
          <SelectGroup key={group}>
            <SelectLabel className="text-[10px]">{t(`typeGroups.${group}`)}</SelectLabel>
            {catalog.templateTypes
              .filter((type) => type.group === group)
              .map((type) => (
                <SelectItem
                  key={type.value}
                  value={type.value}
                  textValue={text(type.value, "label")}
                  className="py-2"
                >
                  <span className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium leading-tight">
                      {text(type.value, "label")}
                    </span>
                    {detailed ? (
                      <span className="text-[10px] text-on-surface-variant leading-snug">
                        {text(type.value, "description")}
                      </span>
                    ) : null}
                  </span>
                </SelectItem>
              ))}
          </SelectGroup>
        ))}
        {known ? null : <SelectItem value={scalar}>{scalar}</SelectItem>}
      </SelectContent>
    </Select>
  );
}

/** The "list of" toggle for leaf types (structures cannot be lists). */
export function ListToggle({
  value,
  onChange,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  const t = useTranslations("workflows.builder.schema");
  const catalog = useCatalog();
  const listable = catalog?.templateTypes.find(
    (type) => type.value === scalarType(value)
  )?.listable;
  if (!catalog || !listable) return null;
  return (
    <label
      className={cn(
        "flex items-center gap-1.5 text-[10px] text-on-surface-variant cursor-pointer",
        className
      )}
      title={t("listModeHint")}
    >
      <input
        type="checkbox"
        className="size-3.5 rounded border-border text-primary focus-visible:ring-2 focus-visible:ring-ring/30"
        checked={isListType(value)}
        onChange={(event) => onChange(withList(value, event.target.checked, catalog))}
      />
      {t("listModeLabel")}
    </label>
  );
}
