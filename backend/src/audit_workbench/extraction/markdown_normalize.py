"""Normalize NuExtract markdown into clean preview text for the UI."""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

_TABLE_RE = re.compile(r"<table\b[\s\S]*?</table>", re.IGNORECASE)
_CELL_RE = re.compile(r"<t[dh]\b[^>]*>([\s\S]*?)</t[dh]>", re.IGNORECASE)
_ROW_RE = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
_FIGURE_RE = re.compile(r"<figure\b[\s\S]*?</figure>", re.IGNORECASE)
_IMG_RE = re.compile(r'<img\b[^>]*alt="([^"]*)"[^>]*>', re.IGNORECASE)
_PAGE_HEADER_RE = re.compile(r"^## Page \d+$", re.MULTILINE)
_LABEL_VALUE_RE = re.compile(
    r"^([A-Za-zÀ-ÿ][\w\s\-/'()]{0,40}?)\s*:\s*(.+)$",
)
_RUNON_TOTAL_RE = re.compile(
    r"(Total HT\s+[\d\s.,]+)(Total TVA\s+[\d\s.,]+)(Total TTC\s+[\d\s.,]+)",
    re.IGNORECASE,
)


def _strip_tags(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _html_table_to_markdown(table_html: str) -> str:
    rows: list[list[str]] = []
    for row_html in _ROW_RE.findall(table_html):
        cells = [_strip_tags(c) for c in _CELL_RE.findall(row_html)]
        if any(cells):
            rows.append(cells)
    if not rows:
        return _strip_tags(table_html)

    width = max(len(r) for r in rows)
    norm = [r + [""] * (width - len(r)) for r in rows]
    header = norm[0]
    body = norm[1:] if len(norm) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _convert_html_tables(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        md = _html_table_to_markdown(match.group(0))
        return f"\n\n{md}\n\n"

    return _TABLE_RE.sub(repl, text)


def _convert_figures(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        block = match.group(0)
        img = _IMG_RE.search(block)
        if img:
            alt = img.group(1).strip() or "Document image"
            return f"\n\n*[Image: {alt}]*\n\n"
        return "\n\n*[Image]*\n\n"

    return _FIGURE_RE.sub(repl, text)


def _strip_html_wrappers(text: str) -> str:
    text = re.sub(r"</?(?:html|body|div|center)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = _IMG_RE.sub(r"\n\n*[Image: \1]*\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def _fix_runon_lines(text: str) -> str:
    text = _RUNON_TOTAL_RE.sub(r"\1\n\2\n\3", text)
    text = re.sub(
        r"(Total HT\s+)([\d\s.,]+)(Total TVA\s+)([\d\s.,]+)(Total TTC\s+)([\d\s.,]+)",
        r"Total HT \2\nTotal TVA \4\nTotal TTC \6",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _emphasize_label_line(line: str) -> str:
    if line.startswith("#"):
        return line
    match = _LABEL_VALUE_RE.match(line)
    if not match:
        return line
    label, value = match.group(1).strip(), match.group(2).strip()
    if len(label) > 35 or not value:
        return line
    return f"**{label}:** {value}"


def _looks_like_structured_markdown(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.startswith("{") and stripped.endswith("}"):
        return False
    body = _PAGE_HEADER_RE.sub("", stripped).strip()
    if not body:
        return False
    return bool(re.search(r"^#{1,6}\s|\*\*|^<table\b", body, re.IGNORECASE | re.MULTILINE))


def format_plain_markdown_lines(lines: Iterable[str]) -> str:
    """Turn document markdown lines into preview-friendly paragraphs."""
    blocks: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        blocks.append("\n\n".join(_emphasize_label_line(line) for line in current))
        current.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush()
            continue
        current.append(line)

    flush()
    return "\n\n".join(block for block in blocks if block.strip())


def _format_plain_document_markdown(text: str) -> str:
    if _looks_like_structured_markdown(text):
        return text

    parts = _PAGE_HEADER_RE.split(text)
    headers = _PAGE_HEADER_RE.findall(text)
    if not headers:
        return format_plain_markdown_lines(text.splitlines())

    sections: list[str] = []
    for index, body in enumerate(parts):
        if index < len(headers):
            sections.append(headers[index])
        cleaned = format_plain_markdown_lines(body.splitlines())
        if cleaned:
            sections.append(cleaned)
    return "\n\n".join(section for section in sections if section.strip())


def _collapse_blank_lines(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    out: list[str] = []
    blank = 0
    for ln in lines:
        if not ln.strip():
            blank += 1
            if blank <= 2:
                out.append("")
            continue
        blank = 0
        out.append(ln)
    return "\n".join(out).strip()


def normalize_document_markdown(text: str | None) -> str | None:
    """Convert mixed HTML/markdown NuExtract output into readable markdown."""
    if not text or not text.strip():
        return text
    normalized = text.strip()
    normalized = _convert_figures(normalized)
    normalized = _convert_html_tables(normalized)
    normalized = _strip_html_wrappers(normalized)
    normalized = _fix_runon_lines(normalized)
    normalized = _format_plain_document_markdown(normalized)
    normalized = _collapse_blank_lines(normalized)
    return normalized or text.strip()
