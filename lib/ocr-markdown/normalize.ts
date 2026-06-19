/** Client-side OCR markdown cleanup (mirrors backend ocr_markdown.py). */

const TABLE_RE = /<table\b[\s\S]*?<\/table>/gi;
const ROW_RE = /<tr\b[^>]*>([\s\S]*?)<\/tr>/gi;
const CELL_RE = /<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi;
const FIGURE_RE = /<figure\b[\s\S]*?<\/figure>/gi;
const IMG_RE = /<img\b[^>]*alt="([^"]*)"[^>]*>/gi;
const PAGE_HEADER_RE = /^## Page \d+$/gm;
const LABEL_VALUE_RE = /^([A-Za-zÀ-ÿ][\w\s\-/'()]{0,40}?)\s*:\s*(.+)$/;
const RUNON_TOTAL_RE =
  /(Total HT\s+[\d\s.,]+)(Total TVA\s+[\d\s.,]+)(Total TTC\s+[\d\s.,]+)/gi;
const STRUCTURED_MARKDOWN_RE = /^#{1,6}\s|\*\*|^<table\b/im;

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

function convertFigures(text: string): string {
  return text.replace(FIGURE_RE, (figure) => {
    const img = IMG_RE.exec(figure);
    IMG_RE.lastIndex = 0;
    const alt = img?.[1]?.trim() || "Document image";
    return `\n\n*[Image: ${alt}]*\n\n`;
  });
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

function emphasizeLabelLine(line: string): string {
  if (line.startsWith("#")) return line;
  const match = LABEL_VALUE_RE.exec(line);
  if (!match) return line;
  const label = match[1].trim();
  const value = match[2].trim();
  if (label.length > 35 || !value) return line;
  return `**${label}:** ${value}`;
}

function looksLikeStructuredMarkdown(text: string): boolean {
  const stripped = text.trim();
  if (!stripped) return false;
  if (stripped.startsWith("{") && stripped.endsWith("}")) return false;
  const body = stripped.replace(PAGE_HEADER_RE, "").trim();
  if (!body) return false;
  return STRUCTURED_MARKDOWN_RE.test(body);
}

export function formatPlainOcrLines(lines: string[]): string {
  const blocks: string[] = [];
  const current: string[] = [];

  const flush = () => {
    if (!current.length) return;
    blocks.push(current.map(emphasizeLabelLine).join("\n\n"));
    current.length = 0;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flush();
      continue;
    }
    current.push(line);
  }

  flush();
  return blocks.filter(Boolean).join("\n\n");
}

function formatPlainOcrMarkdown(text: string): string {
  if (looksLikeStructuredMarkdown(text)) return text;

  const headers = text.match(PAGE_HEADER_RE) ?? [];
  if (!headers.length) {
    return formatPlainOcrLines(text.split("\n"));
  }

  const parts = text.split(PAGE_HEADER_RE);
  const sections: string[] = [];
  for (let index = 0; index < parts.length; index += 1) {
    if (index < headers.length) {
      sections.push(headers[index]);
    }
    const cleaned = formatPlainOcrLines(parts[index].split("\n"));
    if (cleaned) sections.push(cleaned);
  }
  return sections.filter(Boolean).join("\n\n");
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
  normalized = convertFigures(normalized);
  normalized = convertHtmlTables(normalized);
  normalized = stripHtmlWrappers(normalized);
  normalized = fixRunonLines(normalized);
  normalized = formatPlainOcrMarkdown(normalized);
  normalized = collapseBlankLines(normalized);
  return normalized || text.trim();
}

export function splitOcrMarkdownPages(text: string): { header: string; body: string }[] {
  const normalized = normalizeOcrMarkdown(text);
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
