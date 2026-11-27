"""Tier-1 SSIM visual diff across PDF incremental revisions (using pypdfium2 + scikit-image)."""

from typing import cast

import numpy as np
from PIL import Image, ImageDraw
from skimage.metrics import structural_similarity

from repody_common.contracts import FraudFinding
from repody_fraud.detectors.render import (
    contours_to_normalized_bboxes,
    encode_png,
    extract_pdf_revisions,
    render_pages_rgb,
)
from repody_fraud.schemas.analyses import DetectorResult, GeneratedEvidence


def _to_luma(rgb: np.ndarray) -> np.ndarray:
    return np.asarray(Image.fromarray(rgb).convert("L"), dtype=np.uint8)


def _render_diff_artifact(
    first_rgb: np.ndarray,
    latest_rgb: np.ndarray,
    change_mask: np.ndarray,
) -> bytes:
    """Render side-by-side revision comparison with changed regions highlighted in red."""
    target_h = max(first_rgb.shape[0], latest_rgb.shape[0])
    target_w = max(first_rgb.shape[1], latest_rgb.shape[1])

    left = Image.fromarray(first_rgb).resize((target_w, target_h))
    right = Image.fromarray(latest_rgb).resize((target_w, target_h)).convert("RGBA")

    overlay = np.zeros((target_h, target_w, 4), dtype=np.uint8)
    resized_mask = np.asarray(
        Image.fromarray(change_mask).resize((target_w, target_h), Image.Resampling.NEAREST)
    )
    changed = resized_mask > 0
    overlay[changed] = [239, 68, 68, 120]
    right_highlighted = Image.alpha_composite(right, Image.fromarray(overlay, mode="RGBA")).convert(
        "RGB"
    )

    canvas = Image.new("RGB", (target_w * 2 + 12, target_h), color=(24, 24, 27))
    canvas.paste(left, (0, 0))
    canvas.paste(right_highlighted, (target_w + 12, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(target_w + 2, 0), (target_w + 9, target_h)], fill=(239, 68, 68))
    return encode_png(canvas)


def analyze_pdf_revision_diff(data: bytes, *, max_pages: int = 10) -> DetectorResult:
    """Compare earliest vs latest PDF revision visually and emit diff PNG evidence."""
    revisions = extract_pdf_revisions(data)
    if len(revisions) < 2:
        return DetectorResult()

    try:
        earliest_pages = render_pages_rgb(
            revisions[0], "application/pdf", max_pages=max_pages, dpi=120
        )
        latest_pages = render_pages_rgb(
            revisions[-1], "application/pdf", max_pages=max_pages, dpi=120
        )
    except Exception:
        return DetectorResult()

    findings: list[FraudFinding] = []
    evidence: list[tuple[int, GeneratedEvidence]] = []

    for page_num, (prev_rgb, curr_rgb) in enumerate(
        zip(earliest_pages, latest_pages, strict=False), start=1
    ):
        if prev_rgb.shape != curr_rgb.shape:
            curr_resized = np.asarray(
                Image.fromarray(curr_rgb).resize((prev_rgb.shape[1], prev_rgb.shape[0])),
                dtype=np.uint8,
            )
        else:
            curr_resized = curr_rgb

        prev_gray = _to_luma(prev_rgb)
        curr_gray = _to_luma(curr_resized)
        raw_score, raw_diff = cast(
            tuple[float, np.ndarray],
            structural_similarity(prev_gray, curr_gray, full=True),
        )
        score = float(raw_score)
        diff_map = np.asarray(raw_diff, dtype=np.float32)

        if score >= 0.995:
            continue

        change_mask = ((1.0 - diff_map) > 0.25).astype(np.uint8) * 255
        boxes = contours_to_normalized_bboxes(change_mask, min_area=24, limit=5)
        diff_png = _render_diff_artifact(prev_rgb, curr_resized, change_mask)

        idx = len(findings)
        findings.append(
            FraudFinding(
                detector="pdf_revision_diff",
                tier=1,
                code="PDF_REVISION_VISUAL_CHANGE",
                severity="critical",
                title="Visible content altered across PDF revisions",
                detail=(
                    f"Revision 1 vs latest page {page_num} differs visually "
                    f"(SSIM={score:.4f}, changed_regions={len(boxes)})."
                ),
                page=page_num,
                bbox=boxes[0] if boxes else None,
            )
        )
        evidence.append(
            (
                idx,
                GeneratedEvidence(
                    kind="pdf_revision_diff",
                    mime_type="image/png",
                    data=diff_png,
                    file_name=f"revision-diff-p{page_num}.png",
                ),
            )
        )

    return DetectorResult(findings=findings, evidence=evidence)
