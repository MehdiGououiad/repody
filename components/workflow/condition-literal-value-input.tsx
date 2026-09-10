"use client";

import type { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LiteralInputKind } from "@/lib/rules/condition-input-kind";
import { cn } from "@/lib/utils";

export function literalPlaceholderForKind(
  kind: LiteralInputKind,
  t: ReturnType<typeof useTranslations>
): string | undefined {
  switch (kind) {
    case "date":
      return t("literalDatePlaceholder");
    case "datetime-local":
      return t("literalDateTimePlaceholder");
    case "time":
      return t("literalTimePlaceholder");
    case "number":
      return t("literalNumberPlaceholder");
    default:
      return t("literalPlaceholder");
  }
}

export function LiteralValueInput({
  value,
  onChange,
  inputKind,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  inputKind: LiteralInputKind;
  placeholder?: string;
}) {
  if (inputKind === "boolean") {
    return (
      <Select value={value || "true"} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="true" className="text-xs font-mono">
            true
          </SelectItem>
          <SelectItem value="false" className="text-xs font-mono">
            false
          </SelectItem>
        </SelectContent>
      </Select>
    );
  }

  return (
    <Input
      type={inputKind === "text" ? "text" : inputKind}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      step={inputKind === "number" ? "any" : undefined}
      className={cn("h-8 text-xs font-mono", inputKind === "datetime-local" ? "w-48" : "w-40")}
    />
  );
}
