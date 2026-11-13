import { SITE } from "@/lib/site";

const ENDPOINT = `${SITE.appUrl}/api/v1`;
const NEXT_LINE = " \\";

/** The two calls of the API, as the product's API panel writes them, and what each returns. */
export function ApiExample({ t }: { t: { send: string; read: string } }) {
  const calls = [
    {
      title: t.send,
      method: "POST",
      code: [
        `curl -X POST "${ENDPOINT}/workflows/wf-3c7a52d0/runs"${NEXT_LINE}`,
        `  -H "Authorization: Bearer $REPODY_KEY"${NEXT_LINE}`,
        `  -F "documents=Facture" -F "files=@facture.pdf"${NEXT_LINE}`,
        `  -F "documents=Bon de commande" -F "files=@commande.pdf"`,
      ],
      response: ["HTTP/1.1 202 Accepted", "", `{ "runId": "run-01a1d3", "status": "queued" }`],
    },
    {
      title: t.read,
      method: "GET",
      code: [
        `curl "${ENDPOINT}/runs/run-01a1d3"${NEXT_LINE}`,
        `  -H "Authorization: Bearer $REPODY_KEY"`,
      ],
      response: [
        "HTTP/1.1 200 OK",
        "",
        "{",
        `  "status": "done",`,
        `  "result": {`,
        `    "status": "warning",`,
        `    "summary": {`,
        `      "total": 6, "passed": 5, "failed": 1,`,
        `      "fieldsExtracted": 18`,
        "    },",
        `    "documents": [ … ],`,
        `    "ruleResults": [ … ]`,
        "  }",
        "}",
      ],
    },
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {calls.map((call, i) => (
        <figure
          key={call.method}
          className="flex min-w-0 flex-col overflow-hidden rounded-xl bg-panel shadow-[0_0_0_1px_var(--line)]"
        >
          <figcaption className="flex items-center gap-3 border-b border-line px-4 py-2.5 text-sm">
            <span className="flex size-5 items-center justify-center rounded-full bg-selected text-xs font-semibold tabular-nums text-ink-2">
              {i + 1}
            </span>
            <span className="font-medium text-ink">{call.title}</span>
            <span className="ms-auto rounded bg-accent-wash px-1.5 py-0.5 font-mono text-xs text-accent-ink">
              {call.method}
            </span>
          </figcaption>
          <pre className="whitespace-pre-wrap px-4 py-4 [overflow-wrap:anywhere] font-mono text-[0.8125rem] leading-relaxed text-ink">
            {call.code.join("\n")}
          </pre>
          <pre className="mt-auto overflow-x-auto border-t border-line bg-canvas px-4 py-4 font-mono text-[0.8125rem] leading-relaxed text-ink-3">
            {call.response.join("\n")}
          </pre>
        </figure>
      ))}
    </div>
  );
}
