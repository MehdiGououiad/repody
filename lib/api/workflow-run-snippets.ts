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

/**
 * Examples of `POST /v1/workflows/{id}/runs`: multipart, one `files` part per document and,
 * in the same order, a `documents` part naming its workflow document type.
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

  const curl = [
    `curl -X POST "${endpoint}" \\`,
    `  -H "${auth}"${slots.length ? " \\" : ""}`,
    ...slots.flatMap((s, i) => [
      `  -F "documents=${s.type}" \\`,
      `  -F "files=@/path/to/${s.file}"${i < slots.length - 1 ? " \\" : ""}`,
    ]),
  ].join("\n");

  const python = [
    "import requests",
    "",
    "response = requests.post(",
    `    "${endpoint}",`,
    `    headers={"Authorization": "Bearer ${apiKey}"},`,
    `    data={"documents": ${JSON.stringify(documentTypes)}},`,
    "    files=[",
    ...slots.map(
      (s) => `        ("files", ("${s.file}", open("${s.file}", "rb"), "application/pdf")),`
    ),
    "    ],",
    ")",
    "print(response.json())",
  ].join("\n");

  const js = [
    "const form = new FormData();",
    ...slots.flatMap((s) => [
      `form.append("documents", "${s.type}");`,
      `form.append("files", /* File for ${s.type} */, "${s.file}");`,
    ]),
    "",
    `const res = await fetch("${endpoint}", {`,
    '  method: "POST",',
    `  headers: { Authorization: "Bearer ${apiKey}" },`,
    "  body: form,",
    "});",
    "const data = await res.json();",
  ].join("\n");

  return { curl, python, js, documentTypes };
}
