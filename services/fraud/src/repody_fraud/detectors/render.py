"""Shared PDF slicing and page rendering utilities for pure detectors."""

import io
import re
from typing import Any

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

_EOF_RE = re.compile(rb"%%EOF\r?\n?")


def extract_pdf_revisions(data: bytes) -> list[bytes]:
    """Slice raw PDF bytes at each ``%%EOF`` marker to recover historical revisions."""
    if not data.lstrip().startswith(b"%PDF-"):
        return []
    revisions: list[bytes] = []
    for match in _EOF_RE.finditer(data):
        candidate = data[: match.end()]
        if len(candidate) > 32:
            revisions.append(candidate)
    return revisions


def render_pages_rgb(
    data: bytes,
    mime_type: str,
    *,
    max_pages: int = 10,
    dpi: int = 150,
) -> list[np.ndarray]:
    """Render PDF pages or decode an image into HxWx3 uint8 RGB numpy arrays."""
    if mime_type == "application/pdf" or data.lstrip().startswith(b"%PDF-"):
        scale: Any = dpi / 72.0
        doc = pdfium.PdfDocument(data)
        try:
            count = min(len(doc), max_pages)
            pages: list[np.ndarray] = []
            for idx in range(count):
                bitmap = doc[idx].render(scale=scale)
                pil_img = bitmap.to_pil().convert("RGB")
                pages.append(np.asarray(pil_img, dtype=np.uint8))
            return pages
        finally:
            doc.close()

    with Image.open(io.BytesIO(data)) as img:
        return [np.asarray(img.convert("RGB"), dtype=np.uint8)]


def encode_png(image: Image.Image) -> bytes:
    """Serialize a Pillow image to PNG bytes."""
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def render_heatmap_overlay(rgb: np.ndarray, anomaly_map: np.ndarray) -> bytes:
    """Render an RGBA Jet heatmap composited on top of ``rgb`` resized to match it."""
    import cv2

    height, width = rgb.shape[:2]
    norm = np.clip(anomaly_map, 0.0, 1.0)
    if norm.shape[:2] != (height, width):
        norm = cv2.resize(norm.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
    u8 = (norm * 255.0).astype(np.uint8)
    colored_bgr = cv2.applyColorMap(u8, cv2.COLORMAP_JET)
    colored_rgb = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
    alpha = (np.clip((norm - 0.15) / 0.85, 0.0, 1.0) * 180.0).astype(np.uint8)
    rgba = np.dstack([colored_rgb, alpha])
    base = Image.fromarray(rgb).convert("RGBA")
    composited = Image.alpha_composite(base, Image.fromarray(rgba, mode="RGBA"))
    return encode_png(composited)


def contours_to_normalized_bboxes(
    binary_mask: np.ndarray,
    *,
    min_area: int = 64,
    limit: int = 10,
) -> list[tuple[float, float, float, float]]:
    """Extract normalized ``(x1, y1, x2, y2)`` bounding boxes from a uint8 mask."""
    import cv2

    height, width = binary_mask.shape[:2]
    if height == 0 or width == 0:
        return []
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[int, tuple[float, float, float, float]]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < min_area:
            continue
        boxes.append(
            (
                area,
                (
                    round(x / width, 4),
                    round(y / height, 4),
                    round((x + w) / width, 4),
                    round((y + h) / height, 4),
                ),
            )
        )
    boxes.sort(key=lambda item: item[0], reverse=True)
    return [bbox for _, bbox in boxes[:limit]]
