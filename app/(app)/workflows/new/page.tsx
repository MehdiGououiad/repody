import dynamic from "next/dynamic";
import { BuilderShellLoader } from "@/components/workflow/builder-shell-loader";
import { requirePermission } from "@/lib/api/server";
import { newWorkflow } from "@/lib/workflow/new-items";

const NewWorkflowBuilder = dynamic(
  () =>
    import("@/components/workflow/builder-shell").then((m) => ({
      default: m.NewWorkflowBuilder,
    })),
  { loading: () => <BuilderShellLoader /> },
);

export default async function NewWorkflowPage() {
  await requirePermission("workflow:write");
  return <NewWorkflowBuilder workflow={newWorkflow()} />;
}
