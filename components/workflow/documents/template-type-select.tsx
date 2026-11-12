"use client";

import { useMessages, useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
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
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  /** Offer object, table and enum types (table columns are scalars only). */
  structures?: boolean;
  detailed?: boolean;
  className?: string;
}) {
  const t = useTranslations("workflows.builder.schema");
  const catalog = useCatalog();
  const text = useTypeText();
  const scalar = scalarType(value);
  const list = isListType(value);
  if (!catalog) return <Skeleton className="h-8" />;
  const known = catalog.templateTypes.some((type) => type.value === scalar);
  const groups = GROUPS.filter((group) => structures || group !== "structure");

  return (
    <Select value={scalar} onValueChange={(next) => onChange(withList(next, list, catalog))}>
      <SelectTrigger
        aria-label={t("type")}
        className={cn(
          "bg-transparent shadow-none hover:bg-hover hover:shadow-none data-[state=open]:bg-hover",
          className
        )}
      >
        <span className="truncate">
          {text(value, "label")}
          {list ? <span className="text-ink-3"> · {t("listModeSuffix")}</span> : null}
        </span>
      </SelectTrigger>
      <SelectContent className="w-72">
        {groups.map((group) => (
          <SelectGroup key={group}>
            <SelectLabel>{t(`typeGroups.${group}`)}</SelectLabel>
            {catalog.templateTypes
              .filter((type) => type.group === group)
              .map((type) => (
                <SelectItem
                  key={type.value}
                  value={type.value}
                  textValue={text(type.value, "label")}
                  className="h-auto items-start py-1.5"
                >
                  <span className="flex flex-col">
                    <span className="text-sm text-ink">{text(type.value, "label")}</span>
                    <span className="text-xs text-ink-3">{text(type.value, "description")}</span>
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
  if (!catalog || !listable) return <span className="hidden md:block" />;
  return (
    <div
      className={cn("flex items-center gap-2 px-2 text-sm text-ink-3 md:justify-center", className)}
      title={t("listModeHint")}
    >
      <Checkbox
        aria-label={t("listModeLabel")}
        checked={isListType(value)}
        onCheckedChange={(on) => onChange(withList(value, on === true, catalog))}
      />
      <span className="md:sr-only" aria-hidden>
        {t("listModeLabel")}
      </span>
    </div>
  );
}
