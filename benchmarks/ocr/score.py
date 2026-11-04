# /// script
# requires-python = ">=3.12"
# dependencies = ["rapidfuzz>=3.14"]
# ///
"""Score every model's outputs against the gold files.

    uv run score.py            # writes results.md and results.json

For each page and model (outputs/<model>/<page>.txt, the model's Markdown or HTML as it came):
  values  share of exact strings found (amounts, ids, dates, IBANs), ignoring spaces and case
  lines   share of text lines found (fuzzy match >= 90, ignoring case, spaces and markup)
  tables  share of table rows found as one output row with every cell (fuzzy >= 90 per cell)
  score   mean of the three (pages without a table: mean of values and lines)
Speed is the median seconds per page from outputs/<model>/timings.json.
"""

from __future__ import annotations

import html
import json
import re
import statistics
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

HERE = Path(__file__).resolve().parent
GOLD, OUT = HERE / "gold", HERE / "outputs"
THRESHOLD = 90
VARIANTS = ("digital", "scan", "lowres", "photo", "fax", "real")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(text)).casefold()
    text = text.replace("\\", "").replace("’", "'").replace("«", '"').replace("»", '"')
    return re.sub(r"\s+", " ", text).strip()


def squash(text: str) -> str:
    return re.sub(r"\s+", "", norm(text))


def plain(raw: str) -> str:
    """The output as text: tags and Markdown markers become spaces, one line per block or row."""
    text = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", raw)
    text = re.sub(r"(?i)</t[dh]>", " | ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"(?m)^\s*(#{1,6}|[-*+]\s|>\s)", " ", text)
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"\$+([^$]*)\$+", r"\1", text)  # inline math markers around plain text
    return text


def rows(raw: str) -> list[list[str]]:
    """Table rows in the output: HTML <tr> rows and Markdown pipe rows."""
    found = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", raw):
        found.append([norm(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)])
    for line in raw.splitlines():
        if line.count("|") >= 2 and not re.fullmatch(r"[\s|:\-]+", line):
            found.append([norm(c) for c in line.strip().strip("|").split("|")])
    return found


def row_found(gold_row: list[str], candidates: list[list[str]]) -> bool:
    cells = [norm(c) for c in gold_row if c.strip()]
    return any(
        all(max((fuzz.ratio(c, o) for o in out), default=0) >= THRESHOLD for c in cells) for out in candidates
    )


def score_page(gold: dict, raw: str) -> dict[str, float | None]:
    text = norm(plain(raw))
    flat = squash(plain(raw))
    values = [v for v in gold["values"] if len(squash(v)) >= 3]
    value_score = sum(squash(v) in flat for v in values) / len(values) if values else None
    lines = gold["lines"]
    line_score = sum(fuzz.partial_ratio(norm(line), text) >= THRESHOLD for line in lines) / len(lines)
    table_rows = [row for table in gold["tables"] for row in table]
    out_rows = rows(raw)
    table_score = sum(row_found(r, out_rows) for r in table_rows) / len(table_rows) if table_rows else None
    parts = [s for s in (value_score, line_score, table_score) if s is not None]
    return {"values": value_score, "lines": line_score, "tables": table_score, "score": sum(parts) / len(parts)}


def mean(xs: list[float | None]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.1f}"


def main() -> None:
    golds = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(GOLD.glob("*.json"))}
    results = {}
    for model_dir in sorted(p for p in OUT.iterdir() if p.is_dir()):
        timings = json.loads((model_dir / "timings.json").read_text()) if (model_dir / "timings.json").exists() else {}
        meta = json.loads((model_dir / "meta.json").read_text()) if (model_dir / "meta.json").exists() else {}
        pages = {}
        for page_id, gold in golds.items():
            out = model_dir / f"{page_id}.txt"
            raw = out.read_text(encoding="utf-8") if out.exists() else ""
            pages[page_id] = score_page(gold, raw) | {"missing": not out.exists()}
        variants = {v: mean([s["score"] for k, s in pages.items() if k.endswith(f"__{v}")]) for v in VARIANTS}
        results[model_dir.name] = {
            "meta": meta,
            "pages": pages,
            "score": mean([s["score"] for s in pages.values()]),
            "values": mean([s["values"] for s in pages.values()]),
            "lines": mean([s["lines"] for s in pages.values()]),
            "tables": mean([s["tables"] for s in pages.values()]),
            "variants": variants,
            "missing": sum(s["missing"] for s in pages.values()),
            "median_s": statistics.median(timings.values()) if timings else None,
        }
    (HERE / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")

    ranked = sorted(results.items(), key=lambda kv: -(kv[1]["score"] or 0))
    lines = [
        f"# OCR benchmark ({len(golds)} pages)",
        "",
        "| Model | Score | Values | Lines | Tables | Digital | Scan | Low-res | Photo | Fax | Payslip | s/page | Missing | Runtime |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, r in ranked:
        v = r["variants"]
        speed = "—" if r["median_s"] is None else f"{r['median_s']:.1f}"
        lines.append(
            f"| {name} | **{pct(r['score'])}** | {pct(r['values'])} | {pct(r['lines'])} | {pct(r['tables'])} | "
            + " | ".join(pct(v[k]) for k in VARIANTS)
            + f" | {speed} | {r['missing']} | {r['meta'].get('runtime', '')} |"
        )
    (HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
