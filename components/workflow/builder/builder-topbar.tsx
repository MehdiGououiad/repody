"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Save, Check, Rocket, ChevronLeft, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export function BuilderTopbar({
  name,
  deployed,
  saving,
  schemaReady,
  onNameChange,
  onSaveDraft,
  onDeploy,
}: {
  name: string;
  deployed: boolean;
  saving: boolean;
  schemaReady: boolean;
  onNameChange: (name: string) => void;
  onSaveDraft: () => void;
  onDeploy: () => void;
}) {
  const t = useTranslations("workflows.builder");
  const tCommon = useTranslations("common");

  return (
    <div className="h-14 border-b border-border/80 flex items-center gap-3 px-4 md:px-6 bg-card/80 backdrop-blur-md shrink-0 z-10">
      <Link
        href="/workflows"
        className="hidden sm:flex items-center gap-1 text-xs text-on-surface-variant hover:text-on-surface transition-colors shrink-0"
      >
        <ChevronLeft className="h-3.5 w-3.5" />
        {t("backToWorkflows")}
      </Link>
      <Separator orientation="vertical" className="hidden sm:block h-5" />

      <Input
        value={name}
        onChange={(e) => onNameChange(e.target.value)}
        placeholder={t("namePlaceholder")}
        className="h-8 max-w-xs text-sm font-display font-semibold border-transparent bg-transparent shadow-none focus-visible:bg-card focus-visible:border-input px-2 -ml-2"
      />

      {deployed ? (
        <Badge variant="success" className="hidden sm:flex gap-1 text-[10px] shrink-0">
          <Check className="h-3 w-3" />
          {t("statusLive")}
        </Badge>
      ) : (
        <Badge variant="outline" className="hidden sm:flex text-[10px] shrink-0 text-on-surface-variant">
          {t("statusDraft")}
        </Badge>
      )}

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="h-8 gap-1.5 text-xs"
          disabled={saving}
          onClick={onSaveDraft}
        >
          <Save className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">
            {saving ? tCommon("saving") : tCommon("saveDraft")}
          </span>
        </Button>

        {!deployed ? (
          <Button
            size="sm"
            className="h-8 gap-1.5 text-xs"
            disabled={!schemaReady}
            onClick={onDeploy}
          >
            <Rocket className="h-3.5 w-3.5" />
            <span>{tCommon("deployWorkflow")}</span>
          </Button>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={onDeploy}
          >
            <Play className="h-3.5 w-3.5" />
            <span>{tCommon("redeployWorkflow")}</span>
          </Button>
        )}
      </div>
    </div>
  );
}
