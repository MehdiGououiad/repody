"use client";

import { useTranslations } from "next-intl";
import { ArrowRight, GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function WorkflowNameGate({
  name,
  onNameChange,
  onContinue,
}: {
  name: string;
  onNameChange: (name: string) => void;
  onContinue: () => void;
}) {
  const t = useTranslations("workflows.builder.nameGate");
  const trimmed = name.trim();

  return (
    <div className="flex flex-1 items-center justify-center p-6 md:p-10">
      <div className="w-full max-w-md space-y-6 text-center">
        <div className="mx-auto size-14 rounded-2xl bg-accent-blue/10 ring-1 ring-accent-blue/20 flex items-center justify-center">
          <GitBranch className="h-7 w-7 text-accent-blue" aria-hidden="true" />
        </div>
        <div className="space-y-2">
          <h1 className="font-display text-2xl font-semibold text-on-surface">{t("title")}</h1>
          <p className="text-sm text-on-surface-variant leading-relaxed">{t("hint")}</p>
        </div>
        <div className="space-y-3 text-left">
          <label htmlFor="workflow-name" className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("label")}
          </label>
          <Input
            id="workflow-name"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder={t("placeholder")}
            className="h-11 text-base font-display font-semibold"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter" && trimmed) onContinue();
            }}
          />
        </div>
        <Button
          size="lg"
          className="w-full gap-2"
          disabled={!trimmed}
          onClick={onContinue}
        >
          {t("continue")}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
