"use client";

import { useMemo } from "react";
import { Box, HardDriveDownload, LoaderCircle, RefreshCw, Zap } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ModelRuntimeConfigPanel } from "@/components/settings/model-runtime-config-panel";
import { startModelAction, type OperatorJob } from "@/lib/api/operator";
import { REPODY_VLM_LABEL } from "@/lib/document-model-branding";
import { useUnifiedModelsCatalog } from "@/lib/hooks/use-catalog-queries";
import { cn } from "@/lib/utils";
import { ACTIVE_STATUSES } from "../settings-shared";

type ModelRow = {
  id: string;
  label: string;
  kind: string;
  runtime: string;
  available: boolean;
  note?: string | null;
  description?: string;
};

export function ModelsTab({
  actionsEnabled,
  jobs,
  onJobCreated,
}: {
  actionsEnabled: boolean;
  jobs: OperatorJob[];
  onJobCreated: (job: OperatorJob) => void;
}) {
  const catalogQuery = useUnifiedModelsCatalog();
  const loading = catalogQuery.isFetching;
  const catalog = catalogQuery.data;

  const refresh = () => {
    void catalogQuery.refetch();
  };

  const rows = useMemo<ModelRow[]>(() => {
    if (!catalog?.models) return [];
    return catalog.models.map((model) => ({
      id: model.id,
      label: model.label,
      kind: model.kind === "validation"
        ? "Validation LLM"
        : model.markdownOnly
          ? "OCR model"
          : "Vision model",
      runtime: model.runtime || REPODY_VLM_LABEL,
      available: model.available !== false,
      note: model.availabilityNote,
      description: model.description,
    }));
  }, [catalog]);

  const runAction = async (action: "pull" | "warmup", model: string) => {
    try {
      const job = await startModelAction(action, model);
      onJobCreated(job);
      toast.success(`${job.label} started`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Action failed");
    }
  };

  return (
    <div className="space-y-6">
      <section className="panel-elevated rounded-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-border bg-surface-container-low flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">Model inventory</h2>
            <p className="text-sm text-on-surface-variant mt-1">
              Catalog availability plus effective runtime knobs (env vars, preprocessing, host inference).
            </p>
          </div>
          <Button variant="outline" onClick={refresh} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
        <div className="divide-y divide-border">
          {rows.map((model) => {
            const active = jobs.find(
              (job) => ACTIVE_STATUSES.has(job.status) && job.label.includes(model.label)
            );
            return (
              <div key={model.id} className="px-6 py-4 flex flex-col lg:flex-row lg:items-center gap-4">
                <div className="size-11 rounded-xl bg-surface-container-low border border-border flex items-center justify-center shrink-0">
                  <Box className="h-5 w-5 text-primary" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-sm">{model.label}</p>
                    <Badge variant={model.available ? "success" : "danger"}>
                      {model.available ? "Available" : "Unavailable"}
                    </Badge>
                    <Badge variant="outline">{model.kind}</Badge>
                    <Badge variant="outline">{model.runtime}</Badge>
                  </div>
                  {model.description ? (
                    <p className="text-xs text-on-surface-variant mt-1">{model.description}</p>
                  ) : null}
                  {model.note ? <p className="text-xs text-danger mt-1">{model.note}</p> : null}
                </div>
                <Button
                  variant="outline"
                  disabled={!actionsEnabled || !model.available || !!active}
                  onClick={() => void runAction("warmup", model.id)}
                >
                  {active ? <LoaderCircle className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}
                  Warm up
                </Button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel-elevated rounded-xl p-6">
        <div className="flex items-start gap-3">
          <span className="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <HardDriveDownload className="h-5 w-5" />
          </span>
          <div className="flex-1">
            <h2 className="font-display text-lg font-semibold">Install {REPODY_VLM_LABEL}</h2>
            <p className="text-sm text-on-surface-variant mt-1">
              Pull and package {REPODY_VLM_LABEL} for Docker Model Runner from the project root:
            </p>
            <code className="mt-3 block rounded-lg border border-border bg-surface-container-low px-3 py-2 text-xs">
              pnpm docker:models:pull
            </code>
          </div>
        </div>
      </section>

      <ModelRuntimeConfigPanel />
    </div>
  );
}
