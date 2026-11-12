"use client";

import { Check, ChevronLeft, Play, Rocket, Save } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import type { BuilderSync } from "@/components/workflow/builder/use-builder-workflow";

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
    <div className="h-14 border-b border-line/80 flex items-center gap-3 px-4 md:px-6 bg-panel/80 shrink-0 z-10">
      <Link
        href="/workflows"
        className="hidden sm:flex items-center gap-1 text-xs text-ink-3 hover:text-ink transition-colors shrink-0"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {t("backToWorkflows")}
      </Link>
      <Separator orientation="vertical" className="hidden sm:block h-5" />

      <Input
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t("namePlaceholder")}
        className="h-8 max-w-xs text-sm font-semibold border-transparent bg-transparent shadow-none focus-visible:bg-panel focus-visible:border-line-strong px-2 -ml-2"
      />

      {deployed ? (
        <Badge variant="success" className="hidden sm:flex gap-1 text-2xs shrink-0">
          <Check className="h-3 w-3" />
          {t("statusLive")}
        </Badge>
      ) : (
        <Badge variant="outline" className="hidden sm:flex text-2xs shrink-0 text-ink-3">
          {t("statusDraft")}
        </Badge>
      )}

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          disabled={sync !== "idle"}
          onClick={onSaveDraft}
        >
          <Save className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">
            {sync === "saving" ? tCommon("saving") : tCommon("saveDraft")}
          </span>
        </Button>

        {!deployed ? (
          <Button
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!schemaReady || sync !== "idle"}
            onClick={onDeploy}
          >
            <Rocket className="h-3.5 w-3.5" />
            <span>{sync === "deploying" ? tCommon("deploying") : tCommon("deployWorkflow")}</span>
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={sync !== "idle"}
            onClick={onDeploy}
          >
            <Play className="h-3.5 w-3.5" />
            <span>{sync === "deploying" ? tCommon("deploying") : tCommon("redeployWorkflow")}</span>
          </Button>
        )}
      </div>
    </div>
  );
}
