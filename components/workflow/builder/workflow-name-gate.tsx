"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** A new workflow starts with its name: one field, one action. */
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
    <form
      className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-5 px-6 pb-[12vh]"
      onSubmit={(e) => {
        e.preventDefault();
        if (trimmed) onContinue();
      }}
    >
      <div className="flex flex-col gap-1.5">
        <h1 className="text-xl font-semibold text-ink">{t("title")}</h1>
        <p className="text-sm text-ink-3">{t("hint")}</p>
      </div>
      <Input
        id="workflow-name"
        aria-label={t("label")}
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t("placeholder")}
        className="h-10 text-base"
        autoFocus
      />
      <Button type="submit" size="lg" disabled={!trimmed} className="self-start">
        {t("continue")}
      </Button>
    </form>
  );
}
