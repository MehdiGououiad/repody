"use client";

import { useShortcut, useShortcutHint } from "@ui-sdk/react/shortcuts";
import { Check, CircleAlert, Dot } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useCan } from "@/components/auth/access-context";
import { Gate } from "@/components/auth/gate";
import { Button } from "@/components/ui/button";
import { BareInput, inlineFieldClass } from "@/components/ui/input";
import { Tooltip } from "@/components/ui/tooltip";
import type { BuilderSync, SaveState } from "@/components/workflow/builder/use-builder-workflow";
import { cn } from "@/lib/utils";

/** The builder's one header row: trail and name, state, the steps, saving, publishing. ⌘S saves. */
export function BuilderTopbar({
  name,
  deployed,
  sync,
  saveState,
  schemaReady,
  steps,
  onNameChange,
  onSaveDraft,
  onDeploy,
}: {
  name: string;
  deployed: boolean;
  sync: BuilderSync;
  saveState: SaveState;
  schemaReady: boolean;
  steps?: React.ReactNode;
  onNameChange: (name: string) => void;
  onSaveDraft: () => void;
  onDeploy: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");
  const tShared = useTranslations("shared");
  const saveHint = useShortcutHint("mod+s");
  const canEdit = useCan("workflow:write");
  useShortcut("mod+s", onSaveDraft, { allowInInput: true, description: tCommon("saveDraft") });

  return (
    <header className="sticky top-0 z-20 flex h-11 shrink-0 items-center gap-2 border-b border-line bg-panel/90 px-3 backdrop-blur-md md:px-4">
      <Link
        href="/workflows"
        className="hidden shrink-0 text-[13px] font-medium text-ink-3 transition-colors duration-100 hover:text-ink sm:block"
      >
        {t("backToWorkflows")}
      </Link>
      <span className="hidden text-ink-4 sm:block" aria-hidden>
        /
      </span>
      <BareInput
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        readOnly={!canEdit}
        placeholder={t("namePlaceholder")}
        aria-label={t("nameLabel")}
        autoFocus={!name}
        className={cn(
          inlineFieldClass,
          "h-7 w-auto min-w-24 max-w-64 font-semibold [field-sizing:content]"
        )}
      />
      <span
        className={cn(
          "hidden h-5 shrink-0 items-center gap-1.5 rounded-full px-2 text-xs font-medium sm:inline-flex",
          deployed ? "bg-pass-wash text-pass-ink" : "bg-selected text-ink-3"
        )}
      >
        <span
          className={cn("size-1.5 rounded-full", deployed ? "bg-pass" : "bg-ink-4")}
          aria-hidden
        />
        {deployed ? t("statusLive") : t("statusDraft")}
      </span>

      {steps ? <div className="mx-auto overflow-x-auto">{steps}</div> : <span className="flex-1" />}

      <div className="flex shrink-0 items-center gap-1">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={saveState.kind}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -3 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "hidden items-center gap-1 text-xs lg:flex",
              saveState.kind === "failed" ? "text-warn-ink" : "text-ink-4"
            )}
            title={saveState.kind === "failed" ? saveState.reason : undefined}
            aria-live="polite"
          >
            {saveState.kind === "saving" ? (
              tCommon("saving")
            ) : saveState.kind === "deploying" ? (
              tCommon("deploying")
            ) : saveState.kind === "failed" ? (
              <>
                <CircleAlert className="size-3" aria-hidden />
                {t("notSaved")}
                <span className="sr-only">: {saveState.reason}</span>
              </>
            ) : saveState.kind === "viewOnly" ? (
              <span title={t("viewOnlyHint")}>{t("viewOnly")}</span>
            ) : saveState.kind === "example" ? (
              <span title={tShared("exampleHint")}>{tShared("example")}</span>
            ) : saveState.kind === "unsaved" ? (
              <>
                <Dot className="size-3" aria-hidden />
                {t("unsaved")}
              </>
            ) : (
              <>
                <Check className="size-3" aria-hidden />
                {t("saved")}
              </>
            )}
          </motion.span>
        </AnimatePresence>
        {canEdit ? (
          <Tooltip label={tCommon("saveDraft")} shortcut={saveHint.text}>
            <Button variant="ghost" disabled={sync !== "idle"} onClick={onSaveDraft}>
              {tCommon("saveDraft")}
            </Button>
          </Tooltip>
        ) : null}
        <Gate permission="workflow:deploy">
          <Button
            variant={deployed ? "secondary" : "primary"}
            disabled={!schemaReady || sync !== "idle"}
            onClick={onDeploy}
            title={!schemaReady ? t("steps.continueBlockedSchema") : undefined}
          >
            {deployed ? tCommon("redeployWorkflow") : tCommon("deployWorkflow")}
          </Button>
        </Gate>
      </div>
    </header>
  );
}
