"""Tier-3 zero-weight visual pixel forensics (ELA, noise residual, ORB copy-move)."""

import io
from collections.abc import Sequence

import cv2
import numpy as np
from PIL import Image

from repody_common.contracts import FraudFinding
from repody_fraud.detectors.render import (
    contours_to_normalized_bboxes,
    render_heatmap_overlay,
    render_pages_rgb,
)
from repody_fraud.schemas.analyses import DetectorResult, GeneratedEvidence


def _compute_ela_map(rgb: np.ndarray, *, quality: int = 90) -> tuple[np.ndarray, float]:
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    recompressed = np.asarray(Image.open(buf).convert("RGB"), dtype=np.float32)
    diff = np.abs(rgb.astype(np.float32) - recompressed).mean(axis=2)
    if float(diff.max()) <= 1.0:
        return np.zeros_like(diff, dtype=np.float32), 0.0
    p99 = float(np.percentile(diff, 99.5))
    norm = np.clip(diff / max(p99, 12.0), 0.0, 1.0).astype(np.float32)
    med = float(np.median(diff))
    mad = float(np.median(np.abs(diff - med))) + 1e-3
    peak_z = float((np.percentile(diff, 99.8) - med) / (1.4826 * mad))
    return norm, peak_z


def _compute_noise_map(rgb: np.ndarray, *, block: int = 32) -> tuple[np.ndarray, float]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    denoised = cv2.medianBlur(gray.astype(np.uint8), 3).astype(np.float32)
    residual = np.abs(gray - denoised)
    h, w = residual.shape
    gh = max(h // block, 1)
    gw = max(w // block, 1)
    grid = np.zeros((gh, gw), dtype=np.float32)
    for r in range(gh):
        for c in range(gw):
            patch = residual[r * block : (r + 1) * block, c * block : (c + 1) * block]
            grid[r, c] = float(np.std(patch))
    med = float(np.median(grid))
    mad = float(np.median(np.abs(grid - med))) + 1e-3
    z_grid = np.abs(grid - med) / (1.4826 * mad)
    peak_z = float(z_grid.max()) if z_grid.size else 0.0
    norm_grid = np.clip((z_grid - 2.0) / 6.0, 0.0, 1.0).astype(np.float32)
    return cv2.resize(norm_grid, (w, h), interpolation=cv2.INTER_LINEAR), peak_z


def _collect_clone_vectors(
    keypoints: Sequence[cv2.KeyPoint],
    matches: Sequence[Sequence[cv2.DMatch]],
) -> dict[tuple[int, int], list[tuple[tuple[float, float], tuple[float, float]]]]:
    buckets: dict[tuple[int, int], list[tuple[tuple[float, float], tuple[float, float]]]] = {}
    for group in matches:
        for m in group:
            if m.queryIdx == m.trainIdx or m.distance > 22:
                continue
            p1 = (float(keypoints[m.queryIdx].pt[0]), float(keypoints[m.queryIdx].pt[1]))
            p2 = (float(keypoints[m.trainIdx].pt[0]), float(keypoints[m.trainIdx].pt[1]))
            if float(np.hypot(p1[0] - p2[0], p1[1] - p2[1])) > 28.0:
                offset = (round((p2[0] - p1[0]) / 12.0), round((p2[1] - p1[1]) / 12.0))
                buckets.setdefault(offset, []).append((p1, p2))
                break
    return buckets


def _detect_copy_move(
    rgb: np.ndarray,
) -> tuple[int, list[tuple[float, float, float, float]], np.ndarray]:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    mask = np.zeros((h, w), dtype=np.float32)
    orb = cv2.ORB.create(nfeatures=1200)
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    if descriptors is None or len(keypoints) < 16:
        return 0, [], mask

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    buckets = _collect_clone_vectors(keypoints, matcher.knnMatch(descriptors, descriptors, k=4))
    if not buckets:
        return 0, [], mask

    strongest = max(buckets.values(), key=len)
    if len(strongest) < 10:
        return len(strongest), [], mask

    binary = np.zeros((h, w), dtype=np.uint8)
    for p1, p2 in strongest:
        cv2.circle(binary, (int(p1[0]), int(p1[1])), 16, 255, -1)
        cv2.circle(binary, (int(p2[0]), int(p2[1])), 16, 255, -1)
    return (
        len(strongest),
        contours_to_normalized_bboxes(binary, min_area=100, limit=6),
        (binary > 0).astype(np.float32),
    )


def _evaluate_page_anomalies(
    page_num: int,
    *,
    ela_map: np.ndarray,
    ela_z: float,
    noise_map: np.ndarray,
    noise_z: float,
    clone_count: int,
    clone_boxes: list[tuple[float, float, float, float]],
) -> list[FraudFinding]:
    page_findings: list[FraudFinding] = []
    if clone_boxes:
        page_findings.append(
            FraudFinding(
                detector="visual_classical",
                tier=3,
                code="VISUAL_COPY_MOVE_CLONE",
                severity="high",
                title="Cloned visual region detected (copy-move)",
                detail=f"ORB geometric matching found {clone_count} consistent cloned keypoint pairs.",
                page=page_num,
                bbox=clone_boxes[0],
            )
        )
    if ela_z > 6.5:
        ela_boxes = contours_to_normalized_bboxes(
            (ela_map > 0.65).astype(np.uint8) * 255, min_area=80, limit=3
        )
        if ela_boxes:
            page_findings.append(
                FraudFinding(
                    detector="visual_classical",
                    tier=3,
                    code="VISUAL_ELA_ANOMALY",
                    severity="medium",
                    title="Localized JPEG Error Level Analysis spike",
                    detail=f"Page {page_num} exhibits uneven compression energy (peak z={ela_z:.1f}).",
                    page=page_num,
                    bbox=ela_boxes[0],
                )
            )
    if noise_z > 7.5:
        noise_boxes = contours_to_normalized_bboxes(
            (noise_map > 0.65).astype(np.uint8) * 255, min_area=200, limit=3
        )
        if noise_boxes:
            page_findings.append(
                FraudFinding(
                    detector="visual_classical",
                    tier=3,
                    code="VISUAL_NOISE_INCONSISTENCY",
                    severity="medium",
                    title="Local image noise-floor inconsistency",
                    detail=f"Page {page_num} has localized sensor/JPEG noise divergence (z={noise_z:.1f}).",
                    page=page_num,
                    bbox=noise_boxes[0],
                )
            )
    return page_findings


def analyze_visual_classical(
    data: bytes,
    mime_type: str,
    *,
    max_pages: int = 5,
) -> DetectorResult:
    """Run classical pixel forensics (ELA, noise inconsistency, copy-move) and emit heatmap PNGs."""
    pages = render_pages_rgb(data, mime_type, max_pages=max_pages, dpi=150)
    findings: list[FraudFinding] = []
    evidence: list[tuple[int, GeneratedEvidence]] = []

    for page_num, rgb in enumerate(pages, start=1):
        ela_map, ela_z = _compute_ela_map(rgb)
        noise_map, noise_z = _compute_noise_map(rgb)
        clone_count, clone_boxes, clone_mask = _detect_copy_move(rgb)

        page_findings = _evaluate_page_anomalies(
            page_num,
            ela_map=ela_map,
            ela_z=ela_z,
            noise_map=noise_map,
            noise_z=noise_z,
            clone_count=clone_count,
            clone_boxes=clone_boxes,
        )
        if not page_findings:
            continue

        combined = np.maximum.reduce([ela_map, noise_map, clone_mask])
        artifact_idx = len(findings)
        findings.extend(page_findings)
        evidence.append(
            (
                artifact_idx,
                GeneratedEvidence(
                    kind="forensic_heatmap",
                    mime_type="image/png",
                    data=render_heatmap_overlay(rgb, combined),
                    file_name=f"classical-heatmap-p{page_num}.png",
                ),
            )
        )

    return DetectorResult(findings=findings, evidence=evidence)
