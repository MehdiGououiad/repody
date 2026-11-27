"""Tier-1 deterministic PDF structure, metadata, incremental update, and JS forensics."""

import io

import pikepdf

from repody_common.contracts import FraudFinding
from repody_fraud.detectors.render import extract_pdf_revisions

SUSPICIOUS_PRODUCERS = (
    "photoshop",
    "gimp",
    "canva",
    "ilovepdf",
    "sejda",
    "pdfescape",
    "smallpdf",
    "inkscape",
    "libreoffice draw",
    "foxit phantom",
    "nitro",
)

OVERLAY_SUBTYPES = frozenset({"/FreeText", "/Square", "/Circle", "/Stamp", "/Redact"})


def _docinfo_str(pdf: pikepdf.Pdf, key: str) -> str:
    if not pdf.docinfo or key not in pdf.docinfo:
        return ""
    return str(pdf.docinfo[key]).strip()


def _has_javascript(pdf: pikepdf.Pdf) -> bool:
    root = pdf.Root
    if "/OpenAction" in root:
        action = root["/OpenAction"]
        if isinstance(action, pikepdf.Dictionary) and str(action.get("/S", "")) == "/JavaScript":
            return True
    names = root.get("/Names")
    if isinstance(names, pikepdf.Dictionary) and "/JavaScript" in names:
        return True
    return any("/AA" in page.obj for page in pdf.pages)


def _check_metadata_and_producer(pdf: pikepdf.Pdf) -> list[FraudFinding]:
    findings: list[FraudFinding] = []
    info_producer = _docinfo_str(pdf, "/Producer")
    info_creator = _docinfo_str(pdf, "/Creator")

    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        xmp_producer = str(meta.get("pdf:Producer", "") or "").strip()
        xmp_creator = str(meta.get("xmp:CreatorTool", "") or "").strip()

    combined_tools = f"{info_producer} {info_creator} {xmp_producer} {xmp_creator}".lower()
    matched_tools = sorted({tool for tool in SUSPICIOUS_PRODUCERS if tool in combined_tools})
    if matched_tools:
        findings.append(
            FraudFinding(
                detector="pdf_structure",
                tier=1,
                code="PDF_SUSPICIOUS_PRODUCER",
                severity="high",
                title="PDF created or edited with high-risk tool",
                detail=(
                    f"Authoring metadata references {', '.join(matched_tools)} "
                    f"(Producer={info_producer or xmp_producer!r})."
                ),
            )
        )

    if info_producer and xmp_producer and info_producer.lower() != xmp_producer.lower():
        findings.append(
            FraudFinding(
                detector="pdf_structure",
                tier=1,
                code="PDF_METADATA_MISMATCH",
                severity="high",
                title="DocInfo and XMP metadata mismatch",
                detail=(
                    f"DocInfo /Producer ({info_producer!r}) conflicts with "
                    f"XMP pdf:Producer ({xmp_producer!r})."
                ),
            )
        )
    return findings


def _find_overlay_pages(pdf: pikepdf.Pdf) -> list[int]:
    pages: list[int] = []
    for idx, page in enumerate(pdf.pages, start=1):
        annots = page.obj.get("/Annots")
        if not isinstance(annots, pikepdf.Array):
            continue
        has_overlay = any(
            isinstance(annot, pikepdf.Dictionary)
            and str(annot.get("/Subtype", "")) in OVERLAY_SUBTYPES
            for annot in annots
        )
        if has_overlay:
            pages.append(idx)
    return pages


def analyze_pdf_structure(data: bytes) -> list[FraudFinding]:
    """Inspect PDF incremental revisions, authoring tools, Info/XMP consistency, and scripts."""
    findings: list[FraudFinding] = []
    revisions = extract_pdf_revisions(data)
    if len(revisions) > 1:
        findings.append(
            FraudFinding(
                detector="pdf_structure",
                tier=1,
                code="PDF_INCREMENTAL_UPDATES",
                severity="medium",
                title="Multiple incremental PDF revisions detected",
                detail=f"PDF contains {len(revisions)} %%EOF revision boundaries.",
            )
        )

    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PdfError as exc:
        findings.append(
            FraudFinding(
                detector="pdf_structure",
                tier=1,
                code="PDF_MALFORMED_STRUCTURE",
                severity="high",
                title="Malformed PDF structure",
                detail=f"pikepdf failed to parse document: {exc}",
            )
        )
        return findings

    with pdf:
        findings.extend(_check_metadata_and_producer(pdf))
        if _has_javascript(pdf):
            findings.append(
                FraudFinding(
                    detector="pdf_structure",
                    tier=1,
                    code="PDF_EMBEDDED_JAVASCRIPT",
                    severity="high",
                    title="Embedded JavaScript action detected",
                    detail="PDF contains JavaScript actions that should never appear in KYC/invoice scans.",
                )
            )
        overlay_pages = _find_overlay_pages(pdf)
        if overlay_pages:
            findings.append(
                FraudFinding(
                    detector="pdf_structure",
                    tier=1,
                    code="PDF_OVERLAY_ANNOTATION",
                    severity="medium",
                    title="Overlay annotations found on PDF page",
                    detail=f"Annotations of overlay/redaction type found on page(s) {overlay_pages}.",
                    page=overlay_pages[0],
                )
            )

    return findings
