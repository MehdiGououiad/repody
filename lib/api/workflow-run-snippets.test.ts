import { describe, expect, it } from "bun:test";
import { buildWorkflowRunSnippets, runStateEndpoint } from "@/lib/api/workflow-run-snippets";
import type { DocumentDef } from "@/lib/types";

const endpoint = "https://app.example.com/api/v1/workflows/wf-1/runs";
const documents = [
  { id: "d1", documentType: "Invoice", schema: [{ id: "f1", name: "total" }] },
] as unknown as DocumentDef[];

describe("workflow run snippets", () => {
  it("name the run read that follows the POST", () => {
    expect(runStateEndpoint(endpoint)).toBe("https://app.example.com/api/v1/runs/{runId}");
  });

  it("start a run, then read it with the same key", () => {
    const { curl, python, js, documentTypes } = buildWorkflowRunSnippets({
      endpoint,
      apiKey: "wbk_test",
      documents,
    });
    expect(documentTypes).toEqual(["Invoice"]);
    for (const snippet of [curl, python, js]) {
      expect(snippet).toContain(endpoint);
      expect(snippet).toContain("https://app.example.com/api/v1/runs/");
      expect(snippet).toContain("Bearer wbk_test");
    }
    expect(curl).toContain('-F "documents=Invoice"');
    expect(python).toContain('state["result"]');
    expect(js).toContain("state.result");
  });
});
