import type { Schema } from "@/lib/api/schema-types";
import type { Workflow } from "@/lib/types";

type WireWorkflow = Schema["WorkflowSchema-Output"];

/**
 * API workflow -> builder workflow. The API types rule kind/scope/severity as plain strings
 * and stores conditions as free-form JSON; the builder narrows them to its own unions.
 */
export function workflowFromWire(wire: WireWorkflow): Workflow {
  return {
    ...wire,
    rules: wire.rules.map((rule) => ({ ...rule, conditions: rule.conditions ?? undefined })),
  } as Workflow;
}
