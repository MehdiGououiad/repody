/** Client-side OCR markdown cleanup (mirrors backend ocr_markdown.py). */

const TABLE_RE = /<table\b[\s\S]*?<\/table>/gi;
const ROW_RE = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
const CELL_RE = /<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi;
const IMG_RE = /<img\b[^>]*alt="([^"]*)"[^>]*>/gi;
const RUNON_TOTAL_RE =
  /(Total HT\s+[\d\s.,]+)(Total TVA\s+[\d\s.,]+)(Total TTC\s+[\d\s.,]+)/gi;

function stripTags(fragment: string): string {
  return fragment
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n)))
    .replace(/\s+/g, " ")
    .trim();
}

function htmlTableToMarkdown(tableHtml: string): string {
  const rows: string[][] = [];
  for (const rowMatch of tableHtml.matchAll(ROW_RE)) {
    const cells: string[] = [];
    for (const cellMatch of rowMatch[1].matchAll(CELL_RE)) {
      cells.push(stripTags(cellMatch[1]));
    }
    if (cells.some(Boolean)) rows.push(cells);
  }
  if (!rows.length) return stripTags(tableHtml);

  const width = Math.max(...rows.map((r) => r.length));
  const norm = rows.map((r) => [...r, ...Array(width - r.length).fill("")]);
  const [header, ...body] = norm;
  const lines = [
    `| ${header.join(" | ")} |`,
    `| ${header.map(() => "---").join(" | ")} |`,
    ...body.map((row) => `| ${row.join(" | ")} |`),
  ];
  return lines.join("\n");
}

function convertHtmlTables(text: string): string {
  return text.replace(TABLE_RE, (table) => `\n\n${htmlTableToMarkdown(table)}\n\n`);
}

function stripHtmlWrappers(text: string): string {
  return text
    .replace(/<\/?(?:html|body|div|center)[^>]*>/gi, "\n")
    .replace(IMG_RE, "\n\n*[Image: $1]*\n\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">");
}

function fixRunonLines(text: string): string {
  return text
    .replace(RUNON_TOTAL_RE, "$1\n$2\n$3")
    .replace(
      /(Total HT\s+)([\d\s.,]+)(Total TVA\s+)([\d\s.,]+)(Total TTC\s+)([\d\s.,]+)/gi,
      "Total HT $2\nTotal TVA $4\nTotal TTC $6"
    );
}

function collapseBlankLines(text: string): string {
  const out: string[] = [];
  let blank = 0;
  for (const ln of text.split("\n")) {
    if (!ln.trim()) {
      blank += 1;
      if (blank <= 2) out.push("");
      continue;
    }
    blank = 0;
    out.push(ln.replace(/\s+$/, ""));
  }
  return out.join("\n").trim();
}

export function normalizeOcrMarkdown(text: string): string {
  if (!text.trim()) return text;
  let normalized = text.trim();
  normalized = convertHtmlTables(normalized);
  normalized = stripHtmlWrappers(normalized);
  normalized = fixRunonLines(normalized);
  normalized = collapseBlankLines(normalized);
  return normalized || text.trim();
}
