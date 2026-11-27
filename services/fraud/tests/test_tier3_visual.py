"""Tier-3 visual forensic tests (classical pixel checks + swappable ONNX session)."""

import numpy as np
from tests.conftest import make_clean_jpeg, make_tampered_copy_move_png

from repody_common.contracts import ArtifactRef
from repody_fraud.detectors.visual_classical import analyze_visual_classical
from repody_fraud.detectors.visual_onnx import OnnxTamperingDetector


def test_classical_visual_distinguishes_clean_from_copy_move_clone() -> None:
    clean_res = analyze_visual_classical(make_clean_jpeg(), "image/jpeg")
    assert all(f.severity not in ("high", "critical") for f in clean_res.findings)

    forged_res = analyze_visual_classical(make_tampered_copy_move_png(), "image/png")
    codes = {f.code for f in forged_res.findings}
    assert "VISUAL_COPY_MOVE_CLONE" in codes
    assert len(forged_res.evidence) >= 1
    assert forged_res.evidence[0][1].data.startswith(b"\x89PNG")


class _FakeTensorMeta:
    name = "input"


class _FakeOnnxSession:
    def get_inputs(self) -> list[_FakeTensorMeta]:
        return [_FakeTensorMeta()]

    def run(self, _output_names: None, feed: dict[str, np.ndarray]) -> list[np.ndarray]:
        tensor = feed["input"]
        _, _, h, w = tensor.shape
        mask = np.zeros((1, 1, h, w), dtype=np.float32)
        mask[:, :, 120:240, 120:260] = 0.95
        return [mask]


def test_onnx_detector_gracefully_skips_when_unconfigured_and_localizes_with_session() -> None:
    ref = ArtifactRef(
        artifact_id="art-1",
        module="core",
        kind="source_document",
        storage_key="k",
        sha256="a" * 64,
        mime_type="image/jpeg",
        byte_size=100,
    )
    img = make_clean_jpeg()

    empty_detector = OnnxTamperingDetector(model_path=None)
    assert empty_detector.analyze_sync(ref, img).findings == []

    active_detector = OnnxTamperingDetector(model_path=None, session=_FakeOnnxSession())
    res = active_detector.analyze_sync(ref, img)
    assert len(res.findings) == 1
    assert res.findings[0].code == "VISUAL_NEURAL_TAMPERING"
    assert res.findings[0].bbox is not None
    assert len(res.evidence) == 1
    assert res.evidence[0][1].data.startswith(b"\x89PNG")
