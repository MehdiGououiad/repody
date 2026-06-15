import type { DocumentDef } from "@/lib/types";

/** Workflow document slots that accept an uploaded file (named type + schema fields). */
export function workflowDocumentSlots(documents: DocumentDef[]): DocumentDef[] {
  return documents.filter(
    (d) => d.documentType.trim() && d.schema.some((f) => f.name.trim())
  );
}

function slugFileName(documentType: string): string {
  const slug = documentType
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug ? `${slug}.pdf` : "document.pdf";
}

function jsonArray(values: string[]): string {
  return JSON.stringify(values);
}

export type WorkflowRunSnippets = {
  curl: string;
  python: string;
  js: string;
  documentTypes: string[];
};

export function buildWorkflowRunSnippets({
  endpoint,
  apiKey,
  documents,
}: {
  endpoint: string;
  apiKey: string;
  documents: DocumentDef[];
}): WorkflowRunSnippets {
  const slots = workflowDocumentSlots(documents);
  const documentTypes = slots.map((d) => d.documentType.trim());
  const typesJson = jsonArray(documentTypes);

  const curlFileLines = slots.map(
    (d) => `  -F "files=@/path/to/${slugFileName(d.documentType)}"`
  );
  const curl =
    slots.length === 0
      ? [
          `curl -X POST "${endpoint}" \\`,
          `  -H "Authorization: Bearer ${apiKey}" \\`,
          `  # Configure document slots first, then add:`,
          `  # -F 'document_types=["Invoice"]' \\`,
          `  # -F "files=@/path/to/invoice.pdf"`,
        ].join("\n")
      : [
          `curl -X POST "${endpoint}" \\`,
          `  -H "Authorization: Bearer ${apiKey}" \\`,
          `  -F 'document_types=${typesJson}' \\`,
          ...curlFileLines,
        ].join("\n");

  const pythonFileTuples = slots
    .map((d) => {
      const name = slugFileName(d.documentType);
      return `        ("files", ("${name}", open("${name}", "rb"), "application/pdf")),`;
    })
    .join("\n");

  const python =
    slots.length === 0
      ? `import requests\n\nresponse = requests.post(\n    "${endpoint}",\n    headers={"Authorization": "Bearer ${apiKey}"},\n)\nprint(response.json())`
      : `import json\nimport requests\n\nresponse = requests.post(\n    "${endpoint}",\n    headers={"Authorization": "Bearer ${apiKey}"},\n    files=[\n${pythonFileTuples}\n        ("document_types", (None, json.dumps(${typesJson}), "application/json")),\n    ],\n)\nprint(response.json())`;

  const jsDecls = slots
    .map((d) => {
      const name = slugFileName(d.documentType);
      const varName = name.replace(/[^a-z0-9]/gi, "_");
      return `const ${varName} = /* File for ${d.documentType.trim()} */;`;
    })
    .join("\n");
  const jsAppends = slots
    .map((d) => {
      const name = slugFileName(d.documentType);
      const varName = name.replace(/[^a-z0-9]/gi, "_");
      return `form.append("files", ${varName}); // ${d.documentType.trim()}`;
    })
    .join("\n");

  const js =
    slots.length === 0
      ? `const res = await fetch("${endpoint}", {\n  method: "POST",\n  headers: { Authorization: "Bearer ${apiKey}" },\n});\nconst data = await res.json();`
      : `${jsDecls}\n\nconst form = new FormData();\nform.append("document_types", JSON.stringify(${typesJson}));\n${jsAppends}\n\nconst res = await fetch("${endpoint}", {\n  method: "POST",\n  headers: { Authorization: "Bearer ${apiKey}" },\n  body: form,\n});\nconst data = await res.json();`;

  return { curl, python, js, documentTypes };
}
