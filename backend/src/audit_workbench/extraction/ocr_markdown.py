"""Normalize document model OCR text into clean markdown for UI preview."""

from __future__ import annotations

import html
import re

_TABLE_RE = re.compile(r"<table\b[\s\S]*?</table>", re.IGNORECASE)
_TAG_RE = re.compile(r"<(/?)([\w]+)([^>]*)>", re.IGNORECASE)
_CELL_RE = re.compile(r"<t[dh]\b[^>]*>([\s\S]*?)</t[dh]>", re.IGNORECASE)
_ROW_RE = re.compile(r"<tr\b[^>]*>([\s\S]*?)</tr>", re.IGNORECASE)
_IMG_RE = re.compile(r'<img\b[^>]*alt="([^"]*)"[^>]*>', re.IGNORECASE)
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


def _strip_html_wrappers(text: str) -> str:
    text = re.sub(r"</?(?:html|body|div|center)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = _IMG_RE.sub(r"\n\n*[Image: \1]*\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


def _fix_runon_lines(text: str) -> str:
    text = _RUNON_TOTAL_RE.sub(r"\1\n\2\n\3", text)
    # Break "Label valueLabel value" patterns common on invoice footers
    text = re.sub(
        r"(Total HT\s+)([\d\s.,]+)(Total TVA\s+)([\d\s.,]+)(Total TTC\s+)([\d\s.,]+)",
        r"Total HT \2\nTotal TVA \4\nTotal TTC \6",
        text,
        flags=re.IGNORECASE,
    )
    return text


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


def normalize_ocr_markdown(text: str | None) -> str | None:
    """Convert mixed HTML/markdown OCR output into readable markdown."""
    if not text or not text.strip():
        return text
    normalized = text.strip()
    normalized = _convert_html_tables(normalized)
    normalized = _strip_html_wrappers(normalized)
    normalized = _fix_runon_lines(normalized)
    normalized = _collapse_blank_lines(normalized)
    return normalized or text.strip()
