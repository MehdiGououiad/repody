"use client";

import { Toggle } from "@ui-sdk/react/toggle";
import { List } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectGroupLabel,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { catalog } from "@/lib/catalog";
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
  const text = useTypeText();
  const scalar = scalarType(value);
  const list = isListType(value);
  const known = catalog.templateTypes.some((type) => type.value === scalar);
  const groups = GROUPS.filter((group) => structures || group !== "structure");

  return (
    <Select
      value={scalar}
      onValueChange={(next: string | null) => next && onChange(withList(next, list, catalog))}
    >
      <SelectTrigger
        aria-label={t("type")}
        className={cn(
          "w-full bg-transparent shadow-none hover:bg-hover hover:shadow-none data-open:bg-hover",
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
            <SelectGroupLabel>{t(`typeGroups.${group}`)}</SelectGroupLabel>
            {catalog.templateTypes
              .filter((type) => type.group === group)
              .map((type) => (
                <SelectItem
                  key={type.value}
                  value={type.value}
                  label={text(type.value, "label")}
                  className="h-auto items-start py-1.5"
                >
                  <span className="flex flex-col">
                    <span className="text-[13px] text-ink">{text(type.value, "label")}</span>
                    <span className="text-xs text-ink-3">{text(type.value, "description")}</span>
                  </span>
                </SelectItem>
              ))}
          </SelectGroup>
        ))}
        {known ? null : (
          <SelectItem value={scalar} label={scalar}>
            {scalar}
          </SelectItem>
        )}
      </SelectContent>
    </Select>
  );
}

/** "List of": a small toggle beside the type, for leaf types (structures cannot be lists). */
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
  const listable = catalog.templateTypes.find((type) => type.value === scalarType(value))?.listable;
  if (!listable) return <span className={className} />;
  return (
    <Toggle
      pressed={isListType(value)}
      onPressedChange={(on) => onChange(withList(value, on, catalog))}
      aria-label={t("listModeLabel")}
      title={t("listModeHint")}
      className={cn(
        "inline-flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-4 transition-colors duration-100 hover:bg-hover hover:text-ink-2 data-pressed:bg-accent-wash data-pressed:text-accent-ink [&_svg]:size-3.5",
        className
      )}
    >
      <List aria-hidden />
    </Toggle>
  );
}
