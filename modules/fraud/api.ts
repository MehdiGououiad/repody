import type { FraudAnalysis } from "./types";

async function extractErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) return body.detail;
  } catch {
    // Ignore non-JSON error body.
  }
  return `HTTP ${response.status}`;
}

export async function analyzeDocument(
  files: readonly File[],
  options?: { extractedDataJson?: string; caseId?: string },
): Promise<FraudAnalysis> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  if (options?.extractedDataJson?.trim()) {
    form.append("extracted_data", options.extractedDataJson.trim());
  }
  if (options?.caseId?.trim()) {
    form.append("case_id", options.caseId.trim());
  }

  const response = await fetch("/api/fraud/v1/analyses", {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await extractErrorDetail(response));
  }
  return (await response.json()) as FraudAnalysis;
}
