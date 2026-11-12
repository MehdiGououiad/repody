"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { BuilderSync } from "@/components/workflow/builder/use-builder-workflow";

/** The builder's header: where you are, the workflow's name (edited in place), its state, its actions. */
export function BuilderTopbar({
  name,
  deployed,
  sync,
  schemaReady,
  onNameChange,
  onSaveDraft,
  onDeploy,
}: {
  name: string;
  deployed: boolean;
  sync: BuilderSync;
  schemaReady: boolean;
  onNameChange: (name: string) => void;
  onSaveDraft: () => void;
  onDeploy: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  return (
    <header className="flex h-11 shrink-0 items-center gap-2 border-b border-line bg-panel px-4 md:px-5">
      <Link
        href="/workflows"
        className="hidden shrink-0 text-sm text-ink-3 transition-colors duration-100 hover:text-ink sm:block"
      >
        {t("backToWorkflows")}
      </Link>
      <span className="hidden text-ink-4 sm:block" aria-hidden>
        /
      </span>
      <input
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t("namePlaceholder")}
        aria-label={t("nameLabel")}
        className="h-7 min-w-0 max-w-sm flex-1 rounded-md bg-transparent px-1.5 text-sm font-medium text-ink outline-none transition-colors duration-100 placeholder:text-ink-4 hover:bg-hover focus-visible:bg-field focus-visible:shadow-[inset_0_0_0_1px_var(--accent)] focus-visible:outline-none"
      />
      <Badge
        variant={deployed ? "success" : "outline"}
        withDot={deployed}
        className="hidden sm:inline-flex"
      >
        {deployed ? t("statusLive") : t("statusDraft")}
      </Badge>
      <div className="ms-auto flex shrink-0 items-center gap-1.5">
        <span className="hidden text-xs text-ink-4 md:inline" aria-live="polite">
          {sync === "saving"
            ? tCommon("saving")
            : sync === "deploying"
              ? tCommon("deploying")
              : null}
        </span>
        <Button variant="ghost" size="sm" disabled={sync !== "idle"} onClick={onSaveDraft}>
          {tCommon("saveDraft")}
        </Button>
        <Button
          size="sm"
          variant={deployed ? "secondary" : "default"}
          disabled={!schemaReady || sync !== "idle"}
          onClick={onDeploy}
          title={!schemaReady ? t("steps.continueBlockedSchema") : undefined}
        >
          {deployed ? tCommon("redeployWorkflow") : tCommon("deployWorkflow")}
        </Button>
      </div>
    </header>
  );
}
