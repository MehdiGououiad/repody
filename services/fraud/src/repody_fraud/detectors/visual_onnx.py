"""Tier-3 swappable ONNX neural tampering localization (MIT Mesorch / IML-ViT)."""

import asyncio
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import onnxruntime as ort

from repody_common.contracts import ArtifactRef, FraudFinding
from repody_fraud.detectors.render import (
    contours_to_normalized_bboxes,
    render_heatmap_overlay,
    render_pages_rgb,
)
from repody_fraud.schemas.analyses import DetectorResult, GeneratedEvidence

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _sigmoid(arr: np.ndarray) -> np.ndarray:
    clipped = np.clip(arr, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


class OnnxTamperingDetector:
    """Air-gapped ONNX inference wrapper implementing ``repody_common.ports.FraudDetector``."""

    name = "visual_onnx"
    tier = 3

    def __init__(
        self,
        model_path: str | None,
        *,
        input_size: int = 512,
        threshold: float = 0.5,
        session: Any | None = None,
    ) -> None:
        self._model_path = model_path
        self._input_size = input_size
        self._threshold = threshold
        self._session = session

    def _get_session(self) -> Any | None:
        if self._session is not None:
            return self._session
        if not self._model_path or not Path(self._model_path).is_file():
            return None
        available = ort.get_available_providers()
        providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
        self._session = ort.InferenceSession(
            self._model_path,
            providers=providers or ["CPUExecutionProvider"],
        )
        return self._session

    def analyze_sync(
        self,
        artifact: ArtifactRef,
        data: bytes,
        *,
        max_pages: int = 5,
    ) -> DetectorResult:
        """Run neural mask prediction synchronously (executed in thread pool)."""
        session = self._get_session()
        if session is None:
            return DetectorResult()

        input_name = session.get_inputs()[0].name
        pages = render_pages_rgb(data, artifact.mime_type, max_pages=max_pages, dpi=150)
        findings: list[FraudFinding] = []
        evidence: list[tuple[int, GeneratedEvidence]] = []

        for page_num, rgb in enumerate(pages, start=1):
            resized = (
                cv2.resize(rgb, (self._input_size, self._input_size)).astype(np.float32) / 255.0
            )
            norm = (resized - _IMAGENET_MEAN) / _IMAGENET_STD
            tensor = np.transpose(norm, (2, 0, 1))[np.newaxis, ...].astype(np.float32)

            outputs = session.run(None, {input_name: tensor})
            raw_mask = np.asarray(outputs[0], dtype=np.float32).squeeze()
            if raw_mask.ndim > 2:
                raw_mask = raw_mask[0]
            prob_map = (
                raw_mask
                if (raw_mask.min() >= 0.0 and raw_mask.max() <= 1.0)
                else _sigmoid(raw_mask)
            )

            binary = (prob_map >= self._threshold).astype(np.uint8) * 255
            boxes = contours_to_normalized_bboxes(binary, min_area=64, limit=5)
            tamper_ratio = float((prob_map >= self._threshold).mean())
            if not boxes or tamper_ratio < 0.002:
                continue

            heatmap_png = render_heatmap_overlay(rgb, prob_map)
            idx = len(findings)
            findings.append(
                FraudFinding(
                    detector=self.name,
                    tier=3,
                    code="VISUAL_NEURAL_TAMPERING",
                    severity="high" if tamper_ratio < 0.1 else "critical",
                    title="Neural pixel manipulation hotspot localized",
                    detail=(
                        f"Page {page_num} flagged {tamper_ratio * 100:.2f}% area above "
                        f"threshold={self._threshold:.2f}."
                    ),
                    page=page_num,
                    bbox=boxes[0],
                )
            )
            evidence.append(
                (
                    idx,
                    GeneratedEvidence(
                        kind="forensic_heatmap",
                        mime_type="image/png",
                        data=heatmap_png,
                        file_name=f"neural-heatmap-p{page_num}.png",
                    ),
                )
            )

        return DetectorResult(findings=findings, evidence=evidence)

    async def analyze(
        self,
        artifact: ArtifactRef,
        data: bytes,
        context: dict[str, Any],
    ) -> list[FraudFinding]:
        max_pages = int(context.get("max_pages", 5))
        result = await asyncio.to_thread(
            self.analyze_sync,
            artifact,
            data,
            max_pages=max_pages,
        )
        return result.findings
