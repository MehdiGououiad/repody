#!/usr/bin/env python3
"""Convert docs/ARCHITECTURE.md into a structured Word document."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "ARCHITECTURE.md"
OUT_PATH = ROOT / "ARCHITECTURE.docx"
PNG_DIR = ROOT / "diagrams" / "exports" / "png"

# Map markdown image basenames (without ext) → PNG files
IMAGE_MAP = {
    "sequence-upload-et-run": PNG_DIR / "sequence-upload-et-run.png",
    "sequence-cycle-vie-complet": PNG_DIR / "sequence-cycle-vie-complet.png",
    "architecture-openshift": PNG_DIR / "architecture-openshift.png",
    "architecture-locale": PNG_DIR / "architecture-locale.png",
    "architecture-backend-couches": PNG_DIR / "architecture-backend-couches.png",
    "sequence-auth-oidc": PNG_DIR / "sequence-auth-oidc.png",
}

NAVY = RGBColor(0x1A, 0x36, 0x5D)
ACCENT = RGBColor(0x2B, 0x6C, 0xB0)
GRAY = RGBColor(0x4A, 0x55, 0x68)
TABLE_HEADER_BG = "1A365D"
TABLE_ALT_BG = "F0F4F8"
CODE_BG = "F7FAFC"


def set_run_font(run, *, name="Calibri", size=11, bold=False, italic=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color


def set_paragraph_spacing(p, *, before=0, after=6, line=1.15):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line


def shade_cell(cell, hex_color: str):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_borders(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "CBD5E0")
        borders.append(el)
    tcPr.append(borders)


def add_page_number(paragraph):
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr)
    run._r.append(fld_char_end)


def add_toc_field(paragraph):
    run = paragraph.add_run()
    fld_char_begin = OxmlElement("w:fldChar")
    fld_char_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    fld_char_separate = OxmlElement("w:fldChar")
    fld_char_separate.set(qn("w:fldCharType"), "separate")
    fld_char_end = OxmlElement("w:fldChar")
    fld_char_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char_begin)
    run._r.append(instr)
    run._r.append(fld_char_separate)
    hint = paragraph.add_run(
        "Clic droit → Mettre à jour les champs pour générer le sommaire."
    )
    set_run_font(hint, size=10, italic=True, color=GRAY)
    run2 = paragraph.add_run()
    run2._r.append(fld_char_end)


def configure_styles(doc: Document):
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0x1A, 0x20, 0x2C)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for level, size, before, after in (
        (1, 18, 18, 8),
        (2, 14, 14, 6),
        (3, 12, 10, 4),
        (4, 11, 8, 4),
    ):
        style = styles[f"Heading {level}"]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = NAVY if level <= 2 else ACCENT
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def strip_md_links(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = text.replace("\\`", "`")
    return text


def add_formatted_runs(paragraph, text: str, *, base_size=11, base_color=None):
    """Parse **bold**, *italic*, `code` inline markers."""
    text = strip_md_links(text)
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            run = paragraph.add_run(text[pos : m.start()])
            set_run_font(run, size=base_size, color=base_color)
        token = m.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=base_size, bold=True, color=base_color)
        elif token.startswith("*"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=base_size, italic=True, color=base_color)
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, name="Consolas", size=base_size - 1, color=ACCENT)
        pos = m.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, size=base_size, color=base_color)


def add_code_block(doc: Document, lines: list[str]):
    for line in lines:
        p = doc.add_paragraph()
        set_paragraph_spacing(p, before=0, after=0, line=1.0)
        p.paragraph_format.left_indent = Cm(0.4)
        # light background via shading on paragraph
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), CODE_BG)
        shd.set(qn("w:val"), "clear")
        p._p.get_or_add_pPr().append(shd)
        run = p.add_run(line if line else " ")
        set_run_font(run, name="Consolas", size=9, color=RGBColor(0x2D, 0x37, 0x48))


def add_table(doc: Document, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True

    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        run = p.add_run(strip_md_links(h).replace("**", ""))
        set_run_font(run, size=10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade_cell(cell, TABLE_HEADER_BG)
        set_cell_borders(cell)

    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            p = cell.paragraphs[0]
            add_formatted_runs(p, val, base_size=9)
            if r_idx % 2 == 1:
                shade_cell(cell, TABLE_ALT_BG)
            set_cell_borders(cell)

    doc.add_paragraph()


def try_embed_image(doc: Document, md_path: str, caption: str | None = None):
    name = Path(md_path).stem
    png = IMAGE_MAP.get(name)
    if png and png.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        # Wide diagrams: keep within page margins (~16 cm usable)
        run.add_picture(str(png), width=Cm(15.5))
        if caption:
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_paragraph_spacing(cap, before=2, after=10)
            r = cap.add_run(caption)
            set_run_font(r, size=9, italic=True, color=GRAY)
        return True
    note = doc.add_paragraph()
    set_paragraph_spacing(note, before=4, after=8)
    r = note.add_run(f"[Diagramme : {md_path}]")
    set_run_font(r, size=9, italic=True, color=GRAY)
    return False


def parse_table(lines: list[str], start: int) -> tuple[list[str], list[list[str]], int]:
    header = [c.strip() for c in lines[start].strip().strip("|").split("|")]
    i = start + 1
    # skip separator
    if i < len(lines) and re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", lines[i].strip()):
        i += 1
    rows: list[list[str]] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        # pad/trim to header length
        if len(row) < len(header):
            row += [""] * (len(header) - len(row))
        rows.append(row[: len(header)])
        i += 1
    return header, rows, i


def build_cover(doc: Document, meta: dict[str, str]):
    for _ in range(3):
        doc.add_paragraph()

    brand = doc.add_paragraph()
    brand.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = brand.add_run("REPODY")
    set_run_font(r, name="Calibri", size=28, bold=True, color=NAVY)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(title, before=12, after=18)
    r = title.add_run(
        "Dossier d'architecture fonctionnelle et technique"
    )
    set_run_font(r, size=20, bold=True, color=ACCENT)

    for key, label in (
        ("produit", "Produit"),
        ("objet", "Objet"),
        ("public", "Public visé"),
    ):
        if key not in meta:
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_paragraph_spacing(p, before=4, after=4)
        r1 = p.add_run(f"{label} — ")
        set_run_font(r1, size=11, bold=True, color=NAVY)
        r2 = p.add_run(meta[key])
        set_run_font(r2, size=11, color=GRAY)

    doc.add_paragraph()
    linked = doc.add_paragraph()
    linked.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_paragraph_spacing(linked, before=24, after=6)
    r = linked.add_run(
        "Documents liés : CONTEXT.md · LOCAL.md · CLUSTER.md · EXTRACTION.md · adr/"
    )
    set_run_font(r, size=9, italic=True, color=GRAY)

    conf = doc.add_paragraph()
    conf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = conf.add_run("Document confidentiel — usage interne et clients sous NDA")
    set_run_font(r, size=9, color=GRAY)

    doc.add_page_break()


def convert():
    text = MD_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)

    configure_styles(doc)

    # Header / footer
    header = section.header
    hp = header.paragraphs[0]
    hr = hp.add_run("Repody — Architecture fonctionnelle et technique")
    set_run_font(hr, size=8, color=GRAY)
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = fp.add_run("Page ")
    set_run_font(fr, size=8, color=GRAY)
    add_page_number(fp)
    fr2 = fp.add_run("  |  Confidentiel")
    set_run_font(fr2, size=8, color=GRAY)

    # Extract meta from first lines
    meta: dict[str, str] = {}
    for line in lines[:15]:
        m = re.match(r"\*\*(Produit|Objet du document|Public visé)\s*:\*\*\s*(.+)", line)
        if m:
            key = {"Produit": "produit", "Objet du document": "objet", "Public visé": "public"}[
                m.group(1)
            ]
            meta[key] = strip_md_links(m.group(2)).strip()

    build_cover(doc, meta)

    # TOC page
    toc_title = doc.add_paragraph()
    r = toc_title.add_run("Sommaire")
    set_run_font(r, size=18, bold=True, color=NAVY)
    toc_p = doc.add_paragraph()
    add_toc_field(toc_p)
    note = doc.add_paragraph()
    set_paragraph_spacing(note, before=8, after=8)
    nr = note.add_run(
        "Dans Word : sélectionner le sommaire → clic droit → Mettre à jour les champs → "
        "Mettre à jour entièrement."
    )
    set_run_font(nr, size=9, italic=True, color=GRAY)
    doc.add_page_break()

    i = 0
    in_sommaire = False
    embedded_stems: set[str] = set()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip YAML-like front / initial title (already on cover)
        if i == 0 and stripped.startswith("# "):
            i += 1
            continue

        # Skip meta block after title
        if re.match(r"^\*\*(Produit|Objet du document|Public visé)\s*:\*\*", stripped):
            i += 1
            continue
        if stripped.startswith("Documents liés"):
            i += 1
            continue

        # Horizontal rule
        if stripped == "---":
            i += 1
            if in_sommaire:
                in_sommaire = False
            continue

        # Skip markdown sommaire section (we have TOC field)
        if stripped == "## Sommaire":
            in_sommaire = True
            i += 1
            continue
        if in_sommaire:
            i += 1
            continue

        # Headings
        hm = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if hm:
            level = len(hm.group(1))
            title = strip_md_links(hm.group(2))
            if level == 1:
                word_level = 1
            elif level == 2:
                word_level = 1
            elif level == 3:
                word_level = 2
            else:
                word_level = 3
            doc.add_heading(title, level=word_level)
            i += 1
            continue

        # Code fence
        if stripped.startswith("```"):
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # closing ```
            add_code_block(doc, code_lines)
            continue

        # Table
        if stripped.startswith("|") and i + 1 < len(lines) and re.search(r"\|.*\|", lines[i + 1]):
            headers, rows, i = parse_table(lines, i)
            add_table(doc, headers, rows)
            continue

        # Image
        img = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", stripped)
        if img:
            caption = strip_md_links(img.group(1)) or None
            stem = Path(img.group(2)).stem
            if try_embed_image(doc, img.group(2), caption):
                embedded_stems.add(stem)
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            p = doc.add_paragraph()
            set_paragraph_spacing(p, before=6, after=8)
            p.paragraph_format.left_indent = Cm(0.5)
            add_formatted_runs(p, " ".join(quote_lines), base_size=10, base_color=GRAY)
            continue

        # Bullet list
        if re.match(r"^[-*]\s+", stripped):
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                p = doc.add_paragraph(style="List Bullet")
                set_paragraph_spacing(p, before=1, after=2)
                add_formatted_runs(p, item)
                i += 1
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", stripped):
            while i < len(lines) and re.match(r"^\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                p = doc.add_paragraph(style="List Number")
                set_paragraph_spacing(p, before=1, after=2)
                add_formatted_runs(p, item)
                i += 1
            continue

        # Empty
        if not stripped:
            i += 1
            continue

        # Source: references — embed PNG when export exists and not already inserted
        if stripped.startswith("Source"):
            p = doc.add_paragraph()
            set_paragraph_spacing(p, before=2, after=6)
            add_formatted_runs(p, stripped, base_size=9, base_color=GRAY)
            link = re.search(r"\(([^)]+\.(?:mmd|svg|png|html))\)", stripped)
            tick = re.search(r"`([^`]+\.(?:mmd|svg|png))`", stripped)
            rel = link.group(1) if link else (tick.group(1) if tick else "")
            stem = Path(rel).stem if rel else ""
            if stem and stem not in embedded_stems and stem in IMAGE_MAP and IMAGE_MAP[stem].exists():
                if try_embed_image(doc, rel, f"Diagramme — {stem}"):
                    embedded_stems.add(stem)
            i += 1
            continue

        # Normal paragraph
        p = doc.add_paragraph()
        set_paragraph_spacing(p, before=2, after=6)
        add_formatted_runs(p, stripped)
        i += 1

    doc.save(OUT_PATH)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    print(f"Embedded diagrams: {sorted(embedded_stems)}")


if __name__ == "__main__":
    convert()
