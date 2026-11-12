import type { DocumentDef } from "@/lib/types";

/** Workflow document slots that accept an uploaded file (named type + schema fields). */
export function workflowDocumentSlots(documents: DocumentDef[]): DocumentDef[] {
  return documents.filter((d) => d.documentType.trim() && d.schema.some((f) => f.name.trim()));
}

function slugFileName(documentType: string): string {
  const slug = documentType
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug ? `${slug}.pdf` : "document.pdf";
}

export type WorkflowRunSnippets = {
  curl: string;
  python: string;
  js: string;
  documentTypes: string[];
};

/** `GET /v1/runs/{runId}`, the run a POST started: polled until done or failed. */
export function runStateEndpoint(runEndpoint: string): string {
  return `${runEndpoint.replace(/\/workflows\/[^/]+\/runs$/, "/runs")}/{runId}`;
}

/**
 * Examples of a whole call: `POST /v1/workflows/{id}/runs` (multipart, one `files` part per
 * document and, in the same order, a `documents` part naming its workflow document type), then
 * `GET /v1/runs/{runId}` with the same key until the run is done or failed.
 */
export function buildWorkflowRunSnippets({
  endpoint,
  apiKey,
  documents,
}: {
  endpoint: string;
  apiKey: string;
  documents: DocumentDef[];
}): WorkflowRunSnippets {
  const slots = workflowDocumentSlots(documents).map((d) => ({
    type: d.documentType.trim(),
    file: slugFileName(d.documentType),
  }));
  const documentTypes = slots.map((s) => s.type);
  const auth = `Authorization: Bearer ${apiKey}`;
  const runs = runStateEndpoint(endpoint).replace("/{runId}", "");

  const curl = [
    "# 1. Start a run: 202 with its runId",
    `curl -X POST "${endpoint}" \\`,
    `  -H "${auth}"${slots.length ? " \\" : ""}`,
    ...slots.flatMap((s, i) => [
      `  -F "documents=${s.type}" \\`,
      `  -F "files=@/path/to/${s.file}"${i < slots.length - 1 ? " \\" : ""}`,
    ]),
    "",
    '# 2. Get it until "status" is "done" (the report is in "result") or "failed"',
    `curl "${runs}/RUN_ID" -H "${auth}"`,
  ].join("\n");

  const python = [
    "import time",
    "",
    "import requests",
    "",
    `headers = {"Authorization": "Bearer ${apiKey}"}`,
    "",
    "run = requests.post(",
    `    "${endpoint}",`,
    "    headers=headers,",
    `    data={"documents": ${JSON.stringify(documentTypes)}},`,
    "    files=[",
    ...slots.map(
      (s) => `        ("files", ("${s.file}", open("${s.file}", "rb"), "application/pdf")),`
    ),
    "    ],",
    ")",
    "run.raise_for_status()",
    'run_id = run.json()["runId"]',
    "",
    "while True:",
    `    state = requests.get(f"${runs}/{run_id}", headers=headers).json()`,
    '    if state["status"] in ("done", "failed"):',
    "        break",
    "    time.sleep(1)",
    "",
    'if state["status"] == "failed":',
    '    raise RuntimeError(state["error"])',
    'report = state["result"]',
    'print(report["status"])  # passed, warning or failed',
    'for document in report["documents"]:',
    '    for field in document["fields"]:',
    '        print(document["documentType"], field["key"], field["value"])',
  ].join("\n");

  const js = [
    `const headers = { Authorization: "Bearer ${apiKey}" };`,
    "",
    "const form = new FormData();",
    ...slots.flatMap((s) => [
      `form.append("documents", "${s.type}");`,
      `form.append("files", /* File for ${s.type} */, "${s.file}");`,
    ]),
    "",
    `const run = await fetch("${endpoint}", { method: "POST", headers, body: form });`,
    "const { runId } = await run.json();",
    "",
    "let state;",
    "do {",
    "  await new Promise((resolve) => setTimeout(resolve, 1000));",
    `  state = await (await fetch("${runs}/" + runId, { headers })).json();`,
    '} while (state.status === "queued" || state.status === "running");',
    "",
    'if (state.status === "failed") throw new Error(state.error);',
    "const report = state.result; // report.status: passed, warning or failed",
    "for (const document of report.documents) {",
    "  for (const field of document.fields) console.log(document.documentType, field.key, field.value);",
    "}",
  ].join("\n");

  return { curl, python, js, documentTypes };
}
