"""Shared synthetic forensic fixtures and in-memory test doubles for ``repody_fraud``."""

import io
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pikepdf
import pytest
from PIL import Image, ImageDraw

from repody_common.contracts import ArtifactRef, FraudFinding, FraudSeverity
from repody_common.ids import new_id
from repody_fraud.app.service import FraudService
from repody_fraud.detectors.fingerprint import hamming_distance
from repody_fraud.schemas.analyses import (
    AnalysisMode,
    AnalysisResponse,
    FingerprintMatch,
    PageFingerprint,
)


class InMemoryArtifactStorage:
    """In-memory ``ArtifactStorage`` test double."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get_bytes(self, key: str) -> bytes:
        return self.objects[key][0]


class InMemoryFraudStore:
    """In-memory ``FraudStore`` test double with perceptual Hamming search."""

    def __init__(self) -> None:
        self.analyses: dict[str, AnalysisResponse] = {}
        self.fingerprints: list[dict[str, Any]] = []

    async def ping(self) -> bool:
        return True

    async def save_analysis(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        mode: AnalysisMode,
        risk_score: int,
        severity: FraudSeverity,
        short_circuit_recommended: bool,
        requires_four_eyes: bool,
        findings: list[FraudFinding],
        generated_artifacts: list[ArtifactRef],
        explanation: str | None,
    ) -> AnalysisResponse:
        resp = AnalysisResponse(
            id=analysis_id,
            case_id=case_id,
            account_id=account_id,
            mode=mode,
            risk_score=risk_score,
            severity=severity,
            short_circuit_recommended=short_circuit_recommended,
            requires_four_eyes=requires_four_eyes,
            findings=list(findings),
            generated_artifacts=list(generated_artifacts),
            explanation=explanation,
            created_at=datetime.now(UTC),
        )
        self.analyses[analysis_id] = resp
        return resp

    async def get_analysis(
        self,
        analysis_id: str,
        *,
        account: str | None,
    ) -> AnalysisResponse | None:
        record = self.analyses.get(analysis_id)
        if record is None or (account is not None and record.account_id != account):
            return None
        return record

    async def store_fingerprints(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        sha256: str,
        fingerprints: list[PageFingerprint],
    ) -> None:
        for fp in fingerprints:
            self.fingerprints.append(
                {
                    "id": new_id("fp"),
                    "analysis_id": analysis_id,
                    "case_id": case_id,
                    "account_id": account_id,
                    "page": fp.page,
                    "sha256": sha256,
                    "phash_bits": fp.phash_bits,
                    "dhash_bits": fp.dhash_bits,
                }
            )

    async def find_similar_fingerprints(
        self,
        *,
        phash_bits: str,
        account: str | None,
        max_distance: int,
        exclude_case_id: str | None,
    ) -> list[FingerprintMatch]:
        matches: list[FingerprintMatch] = []
        for entry in self.fingerprints:
            if account is not None and entry["account_id"] != account:
                continue
            if exclude_case_id is not None and entry["case_id"] == exclude_case_id:
                continue
            dist = hamming_distance(entry["phash_bits"], phash_bits)
            if dist <= max_distance:
                matches.append(
                    FingerprintMatch(
                        fingerprint_id=entry["id"],
                        prior_analysis_id=entry["analysis_id"],
                        prior_case_id=entry["case_id"],
                        page=entry["page"],
                        hamming_distance=dist,
                    )
                )
        matches.sort(key=lambda m: m.hamming_distance)
        return matches[:5]


def _page_pdf_bytes(
    image: Image.Image,
    *,
    info_producer: str,
    xmp_producer: str | None = None,
) -> bytes:
    """Create a clean PDF page wrapping a rendered bitmap image via ``pikepdf``."""
    pdf = pikepdf.Pdf.new()
    width, height = image.size
    page = pdf.add_blank_page(page_size=(width, height))
    raw_rgb = image.convert("RGB").tobytes()
    img_stream = pikepdf.Stream(
        pdf,
        raw_rgb,
        Type=pikepdf.Name("/XObject"),
        Subtype=pikepdf.Name("/Image"),
        Width=width,
        Height=height,
        ColorSpace=pikepdf.Name("/DeviceRGB"),
        BitsPerComponent=8,
    )
    page.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=img_stream))
    page.Contents = pikepdf.Stream(
        pdf,
        f"q {width} 0 0 {height} 0 0 cm /Im0 Do Q".encode("ascii"),
    )
    pdf.docinfo["/Producer"] = info_producer
    with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
        meta["pdf:Producer"] = xmp_producer or info_producer
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def make_clean_pdf(label: str = "INVOICE #2026-001 TOTAL 120.00") -> bytes:
    """Build a valid single-revision PDF with consistent metadata."""
    img = Image.new("RGB", (600, 300), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(24, 24), (576, 276)], outline=(30, 41, 59), width=3)
    draw.text((48, 80), label, fill=(15, 23, 42))
    return _page_pdf_bytes(img, info_producer="RepodyERP 2.0")


def make_tampered_incremental_pdf() -> bytes:
    """Build a real ISO 32000 incremental PDF revision altering visual pixels & /Producer."""
    from pyhanko.pdf_utils import generic
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    img_rev1 = Image.new("RGB", (600, 300), color=(255, 255, 255))
    d1 = ImageDraw.Draw(img_rev1)
    d1.rectangle([(20, 20), (580, 280)], outline=(0, 0, 0), width=4)
    d1.rectangle([(80, 100), (260, 180)], fill=(30, 64, 175))

    rev1_bytes = _page_pdf_bytes(img_rev1, info_producer="OfficialBilling 1.0")
    buf = io.BytesIO(rev1_bytes)
    writer = IncrementalPdfFileWriter(buf, strict=False)
    overlay_ref = writer.add_object(
        generic.StreamObject(stream_data=b"q 0.9 0.1 0.1 rg 320 60 220 140 re f Q")
    )
    writer.add_stream_to_page(0, overlay_ref)
    writer.set_info(
        generic.DictionaryObject(
            {generic.NameObject("/Producer"): generic.TextStringObject("Adobe Photoshop 25.0")}
        )
    )
    writer.write_in_place()
    return buf.getvalue()


def make_js_pdf() -> bytes:
    """Build a PDF containing an embedded ``/OpenAction`` JavaScript dictionary."""
    base = make_clean_pdf("JS CHECK")
    pdf = pikepdf.open(io.BytesIO(base))
    pdf.Root["/OpenAction"] = pikepdf.Dictionary(
        S=pikepdf.Name("/JavaScript"),
        JS="app.alert('test');",
    )
    out = io.BytesIO()
    pdf.save(out)
    return out.getvalue()


def make_clean_jpeg() -> bytes:
    """Create a smooth uniform JPEG image."""
    rng = np.random.default_rng(7)
    arr = np.full((320, 480, 3), 210, dtype=np.int16)
    noise = rng.integers(-6, 7, size=(320, 480, 3), dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def make_tampered_copy_move_png() -> bytes:
    """Create an image with a high-detail textured patch cloned (copy-move) cleanly."""
    rng = np.random.default_rng(42)
    arr = np.full((400, 600, 3), 235, dtype=np.uint8)
    patch = rng.integers(0, 255, size=(120, 120, 3), dtype=np.uint8)
    # Paint the exact textured patch in two distinct locations >= 25px apart.
    arr[40:160, 40:160] = patch
    arr[220:340, 400:520] = patch
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def fraud_store() -> InMemoryFraudStore:
    return InMemoryFraudStore()


@pytest.fixture
def fraud_storage() -> InMemoryArtifactStorage:
    return InMemoryArtifactStorage()


@pytest.fixture
def fraud_service(
    fraud_store: InMemoryFraudStore,
    fraud_storage: InMemoryArtifactStorage,
) -> FraudService:
    return FraudService(store=fraud_store, storage=fraud_storage)
