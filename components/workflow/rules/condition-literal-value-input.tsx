"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LiteralInputKind } from "@/lib/rules/operators";
import { cn } from "@/lib/utils";

const PLACEHOLDERS = {
  text: "literalPlaceholder",
  number: "literalNumberPlaceholder",
  date: "literalDatePlaceholder",
  "datetime-local": "literalDateTimePlaceholder",
  time: "literalTimePlaceholder",
} as const;

/** A literal in the input that fits the type it is compared with. */
export function LiteralValueInput({
  value,
  onChange,
  inputKind,
}: {
  value: string;
  onChange: (value: string) => void;
  inputKind: LiteralInputKind;
}) {
  const t = useTranslations("workflows.builder.rules.conditions");

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
      type={inputKind}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={t(PLACEHOLDERS[inputKind])}
      step={inputKind === "number" ? "any" : undefined}
      className={cn("h-8 text-xs font-mono", inputKind === "datetime-local" ? "w-48" : "w-40")}
    />
  );
}
