import dynamic from "next/dynamic";
import { notFound } from "next/navigation";
import { BuilderShellLoader } from "@/components/workflow/builder-shell-loader";
import { fetchRulesLibrary, fetchWorkflow } from "@/lib/api/client";

const EditWorkflowBuilder = dynamic(
  () =>
    import("@/components/workflow/builder-shell").then((m) => ({
      default: m.EditWorkflowBuilder,
    })),
  { loading: () => <BuilderShellLoader /> }
);

export default async function WorkflowBuilderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [workflow, rulesLibrary] = await Promise.all([
    fetchWorkflow(id),
    fetchRulesLibrary(),
  ]);
  if (!workflow) notFound();

  return (
    <EditWorkflowBuilder workflow={workflow} ruleLibrary={rulesLibrary.rules} />
  );
}
