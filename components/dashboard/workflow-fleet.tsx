import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowUpRight } from "lucide-react";
import { WorkflowTile } from "@/components/dashboard/workflow-tile";
import type { Workflow } from "@/lib/types";

function sortWorkflows(workflows: Workflow[]): Workflow[] {
  const rank = (w: Workflow) => {
    if (w.deployedAt && w.apiStats) return 0;
    if (w.status === "active") return 1;
    if (w.status === "paused") return 2;
    return 3;
  };
  return [...workflows].sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
}

export async function WorkflowFleet({ workflows }: { workflows: Workflow[] }) {
  const t = await getTranslations("dashboard.fleet");

  if (!workflows.length) return null;

  const sorted = sortWorkflows(workflows);
  const deployed = sorted.filter((w) => w.deployedAt && w.apiStats);
  const drafts = sorted.filter((w) => !w.deployedAt || !w.apiStats);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-base font-semibold text-on-surface">{t("title")}</h2>
          <p className="text-xs text-on-surface-variant mt-0.5">{t("hint")}</p>
        </div>
        <Link
          href="/workflows"
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          {t("manageAll")}
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {deployed.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("liveApis", { count: deployed.length })}
          </p>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {deployed.map((workflow) => (
              <WorkflowTile key={workflow.id} workflow={workflow} />
            ))}
          </div>
        </div>
      ) : null}

      {drafts.length > 0 ? (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
            {t("drafts", { count: drafts.length })}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {drafts.map((workflow) => (
              <WorkflowTile key={workflow.id} workflow={workflow} />
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
