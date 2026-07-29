/** Client-side markdown preview helper (strip only; mirrors backend truncate path). */

export function normalizeDocumentMarkdown(text: string): string {
  if (!text.trim()) return text;
  return text.trim();
}

export function splitDocumentMarkdownPages(text: string): { header: string; body: string }[] {
  const normalized = normalizeDocumentMarkdown(text);
  const headers = [...normalized.matchAll(/^## Page (\d+)$/gm)];
  if (!headers.length) {
    return normalized.trim() ? [{ header: "", body: normalized }] : [];
  }

  const sections: { header: string; body: string }[] = [];
  for (let index = 0; index < headers.length; index += 1) {
    const start = headers[index].index ?? 0;
    const end = headers[index + 1]?.index ?? normalized.length;
    const chunk = normalized.slice(start, end).trim();
    const lines = chunk.split("\n");
    const header = lines[0]?.trim() ?? "";
    const body = lines.slice(1).join("\n").trim();
    sections.push({ header, body });
  }
  return sections;
}
