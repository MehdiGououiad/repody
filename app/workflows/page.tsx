import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page-header";
import { PageShell } from "@/components/layout/page-shell";
import { WorkflowsList } from "@/components/workflows/workflows-list";
import { fetchWorkflows } from "@/lib/api/client";

export default async function WorkflowsPage() {
  const [t, tNav, workflows] = await Promise.all([
    getTranslations("workflows"),
    getTranslations("nav"),
    fetchWorkflows().catch(() => []),
  ]);

  return (
    <PageShell>
      <PageHeader
        title={t("title")}
        description={t("description")}
        eyebrow="Pipelines"
        actions={
          <Button asChild>
            <Link href="/workflows/new">
              <Plus className="h-4 w-4" />
              {tNav("newWorkflow")}
            </Link>
          </Button>
        }
      />
      <WorkflowsList initialWorkflows={workflows} />
    </PageShell>
  );
}
