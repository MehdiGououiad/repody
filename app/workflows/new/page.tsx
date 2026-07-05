import dynamic from "next/dynamic";
import { BuilderShellLoader } from "@/components/workflow/builder-shell-loader";
import { shortId } from "@/lib/utils";
import type { Workflow } from "@/lib/types";

const NewWorkflowBuilder = dynamic(
  () =>
    import("@/components/workflow/builder-shell").then((m) => ({
      default: m.NewWorkflowBuilder,
    })),
  { loading: () => <BuilderShellLoader /> }
);

function buildBlankWorkflow(): Workflow {
  return {
    id: `wf-${shortId()}`,
    name: "",
    description: "",
    status: "draft",
    owner: "Me",
    lastRun: null,
    successRate: 0,
    totalRuns: 0,
    documents: [
      {
        id: `doc${shortId()}`,
        documentType: "",
        schema: [],
        extractionMode: "auto",
        validationMode: "logic_only",
        documentModelId: null,
      },
    ],
    rules: [],
  };
}

export default function NewWorkflowPage() {
  return <NewWorkflowBuilder workflow={buildBlankWorkflow()} />;
}
