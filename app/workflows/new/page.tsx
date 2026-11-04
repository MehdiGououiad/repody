import dynamic from "next/dynamic";
import { BuilderShellLoader } from "@/components/workflow/builder-shell-loader";
import { newWorkflow } from "@/lib/workflow/new-items";

const NewWorkflowBuilder = dynamic(
  () =>
    import("@/components/workflow/builder-shell").then((m) => ({
      default: m.NewWorkflowBuilder,
    })),
  { loading: () => <BuilderShellLoader /> }
);

export default function NewWorkflowPage() {
  return <NewWorkflowBuilder workflow={newWorkflow()} />;
}
