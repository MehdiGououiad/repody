"""Orchestration use cases for standalone, pre-check, and post-verify Fraud Shield passes."""

import asyncio
import hashlib
from typing import Any

from repody_common.contracts import (
    ArtifactRef,
    FraudFinding,
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
)
from repody_common.ids import new_id
from repody_common.ports import VisualExplainer
from repody_fraud.app.ports import ArtifactStorage, FraudStore
from repody_fraud.app.scoring import compute_risk_summary
from repody_fraud.detectors.c2pa_provenance import analyze_c2pa_provenance
from repody_fraud.detectors.cross_field import analyze_cross_field_logic
from repody_fraud.detectors.fingerprint import compute_document_fingerprints
from repody_fraud.detectors.pdf_revision_diff import analyze_pdf_revision_diff
from repody_fraud.detectors.pdf_signatures import analyze_pdf_signatures
from repody_fraud.detectors.pdf_structure import analyze_pdf_structure
from repody_fraud.detectors.visual_classical import analyze_visual_classical
from repody_fraud.detectors.visual_onnx import OnnxTamperingDetector
from repody_fraud.schemas.analyses import AnalysisResponse, DetectorResult
from repody_fraud.schemas.errors import NotFoundError, ValidationError
from repody_fraud.settings import get_settings


class FraudService:
    """Runs deterministic Tier-1, logic Tier-2, and visual Tier-3 forensic engines."""

    def __init__(
        self,
        store: FraudStore,
        storage: ArtifactStorage,
        *,
        neural_detector: OnnxTamperingDetector | None = None,
        explainer: VisualExplainer | None = None,
    ) -> None:
        self._store = store
        self._storage = storage
        settings = get_settings()
        self._neural = neural_detector or OnnxTamperingDetector(settings.neural_model_path)
        self._explainer = explainer

    async def _persist_evidence(
        self,
        analysis_id: str,
        result: DetectorResult,
        evidence_bytes: list[bytes],
    ) -> tuple[list[FraudFinding], list[ArtifactRef]]:
        findings = list(result.findings)
        artifacts: list[ArtifactRef] = []

        for finding_idx, item in result.evidence:
            art_id = new_id("art")
            key = f"fraud/{analysis_id}/{art_id}-{item.file_name}"
            await self._storage.put_bytes(key, item.data, item.mime_type)
            evidence_bytes.append(item.data)
            ref = ArtifactRef(
                artifact_id=art_id,
                module="fraud",
                kind=item.kind,
                storage_key=key,
                sha256=hashlib.sha256(item.data).hexdigest(),
                mime_type=item.mime_type,
                byte_size=len(item.data),
            )
            artifacts.append(ref)
            if 0 <= finding_idx < len(findings):
                findings[finding_idx] = findings[finding_idx].model_copy(
                    update={"evidence_artifact_id": art_id}
                )

        return findings, artifacts

    async def _run_tier1_for_blob(
        self,
        *,
        analysis_id: str,
        case_id: str | None,
        account_id: str | None,
        data: bytes,
        mime_type: str,
        sha256_hex: str,
        evidence_bytes: list[bytes],
    ) -> tuple[list[FraudFinding], list[ArtifactRef]]:
        settings = get_settings()
        is_pdf = mime_type == "application/pdf" or data.lstrip().startswith(b"%PDF-")

        findings: list[FraudFinding] = []
        artifacts: list[ArtifactRef] = []

        if is_pdf:
            sig_findings, struct_findings, diff_result = await asyncio.gather(
                asyncio.to_thread(analyze_pdf_signatures, data),
                asyncio.to_thread(analyze_pdf_structure, data),
                asyncio.to_thread(
                    analyze_pdf_revision_diff, data, max_pages=settings.max_pages_to_analyze
                ),
            )
            findings.extend(sig_findings)
            findings.extend(struct_findings)
            diff_findings, diff_artifacts = await self._persist_evidence(
                analysis_id, diff_result, evidence_bytes
            )
            findings.extend(diff_findings)
            artifacts.extend(diff_artifacts)

        c2pa_findings = await asyncio.to_thread(analyze_c2pa_provenance, data, mime_type)
        findings.extend(c2pa_findings)

        fingerprints = await asyncio.to_thread(
            compute_document_fingerprints,
            data,
            mime_type,
            max_pages=settings.max_pages_to_analyze,
        )
        matched_prior: set[str] = set()
        for fp in fingerprints:
            matches = await self._store.find_similar_fingerprints(
                phash_bits=fp.phash_bits,
                account=account_id,
                max_distance=settings.phash_max_hamming_distance,
                exclude_case_id=case_id,
            )
            for match in matches:
                prior_label = match.prior_case_id or match.prior_analysis_id
                if prior_label in matched_prior:
                    continue
                matched_prior.add(prior_label)
                findings.append(
                    FraudFinding(
                        detector="fingerprint",
                        tier=1,
                        code="TEMPLATE_REUSE_DETECTED",
                        severity="high",
                        title="Document matches previously ingested template/scan",
                        detail=(
                            f"Page {fp.page} matches prior case '{prior_label}' "
                            f"(Hamming distance={match.hamming_distance})."
                        ),
                        page=fp.page,
                    )
                )

        if fingerprints:
            await self._store.store_fingerprints(
                analysis_id=analysis_id,
                case_id=case_id,
                account_id=account_id,
                sha256=sha256_hex,
                fingerprints=fingerprints,
            )

        return findings, artifacts

    async def _run_tier3_for_blob(
        self,
        *,
        analysis_id: str,
        artifact_ref: ArtifactRef,
        data: bytes,
        evidence_bytes: list[bytes],
    ) -> tuple[list[FraudFinding], list[ArtifactRef]]:
        settings = get_settings()
        classical_res, neural_res = await asyncio.gather(
            asyncio.to_thread(
                analyze_visual_classical,
                data,
                artifact_ref.mime_type,
                max_pages=settings.max_pages_to_analyze,
            ),
            asyncio.to_thread(
                self._neural.analyze_sync,
                artifact_ref,
                data,
                max_pages=settings.max_pages_to_analyze,
            ),
        )
        combined = DetectorResult(
            findings=[*classical_res.findings, *neural_res.findings],
            evidence=[
                *classical_res.evidence,
                *((idx + len(classical_res.findings), ev) for idx, ev in neural_res.evidence),
            ],
        )
        return await self._persist_evidence(analysis_id, combined, evidence_bytes)

    async def _download_verified(
        self, artifacts: list[ArtifactRef]
    ) -> list[tuple[ArtifactRef, bytes]]:
        blobs: list[tuple[ArtifactRef, bytes]] = []
        for ref in artifacts:
            if ref.kind != "source_document":
                continue
            raw = await self._storage.get_bytes(ref.storage_key)
            if hashlib.sha256(raw).hexdigest().lower() != ref.sha256.lower():
                raise ValidationError(f"Artifact {ref.artifact_id} SHA-256 mismatch.")
            blobs.append((ref, raw))
        return blobs

    async def _maybe_explain(
        self,
        findings: list[FraudFinding],
        evidence_bytes: list[bytes],
    ) -> str | None:
        if self._explainer is None or not evidence_bytes:
            return None
        severe = [f for f in findings if f.severity in ("high", "critical")]
        if not severe:
            return None
        return await self._explainer.explain_region(evidence_bytes[0], severe)

    async def run_pre_check(self, payload: FraudPreCheckInput) -> FraudPreCheckOutput:
        """Run Tier-1 pre-extraction forensics (CPU) on immutable source artifacts."""
        settings = get_settings()
        analysis_id = new_id("frd")
        artifacts_in = payload.artifacts or payload.case.artifacts
        blobs = await self._download_verified(artifacts_in)

        findings: list[FraudFinding] = []
        generated: list[ArtifactRef] = []
        evidence_bytes: list[bytes] = []

        for ref, raw in blobs:
            f_list, a_list = await self._run_tier1_for_blob(
                analysis_id=analysis_id,
                case_id=payload.case.case_id,
                account_id=payload.case.account_id,
                data=raw,
                mime_type=ref.mime_type,
                sha256_hex=ref.sha256,
                evidence_bytes=evidence_bytes,
            )
            findings.extend(f_list)
            generated.extend(a_list)

        score, severity, short_circuit, four_eyes = compute_risk_summary(
            findings,
            short_circuit_threshold=settings.short_circuit_score_threshold,
            four_eyes_threshold=settings.four_eyes_score_threshold,
        )
        await self._store.save_analysis(
            analysis_id=analysis_id,
            case_id=payload.case.case_id,
            account_id=payload.case.account_id,
            mode="pre_check",
            risk_score=score,
            severity=severity,
            short_circuit_recommended=short_circuit,
            requires_four_eyes=four_eyes,
            findings=findings,
            generated_artifacts=generated,
            explanation=None,
        )
        return FraudPreCheckOutput(
            analysis_id=analysis_id,
            risk_score=score,
            severity=severity,
            short_circuit_recommended=short_circuit,
            findings=findings,
            generated_artifacts=generated,
        )

    async def run_post_verify(self, payload: FraudPostVerifyInput) -> FraudPostVerifyOutput:
        """Run Tier-2 logic checks and Tier-3 visual localization after IDP extraction."""
        settings = get_settings()
        analysis_id = new_id("frd")
        artifacts_in = payload.artifacts or payload.case.artifacts
        blobs = await self._download_verified(artifacts_in)

        findings: list[FraudFinding] = list(analyze_cross_field_logic(payload.extracted_data))
        generated: list[ArtifactRef] = []
        evidence_bytes: list[bytes] = []

        for ref, raw in blobs:
            f_list, a_list = await self._run_tier3_for_blob(
                analysis_id=analysis_id,
                artifact_ref=ref,
                data=raw,
                evidence_bytes=evidence_bytes,
            )
            findings.extend(f_list)
            generated.extend(a_list)

        explanation = await self._maybe_explain(findings, evidence_bytes)
        score, severity, short_circuit, four_eyes = compute_risk_summary(
            findings,
            short_circuit_threshold=settings.short_circuit_score_threshold,
            four_eyes_threshold=settings.four_eyes_score_threshold,
        )
        await self._store.save_analysis(
            analysis_id=analysis_id,
            case_id=payload.case.case_id,
            account_id=payload.case.account_id,
            mode="post_verify",
            risk_score=score,
            severity=severity,
            short_circuit_recommended=short_circuit,
            requires_four_eyes=four_eyes,
            findings=findings,
            generated_artifacts=generated,
            explanation=explanation,
        )
        return FraudPostVerifyOutput(
            analysis_id=analysis_id,
            risk_score=score,
            severity=severity,
            requires_four_eyes=four_eyes,
            findings=findings,
            generated_artifacts=generated,
        )

    async def run_standalone_analysis(
        self,
        *,
        files: list[tuple[str, bytes, str]],
        extracted_data: dict[str, Any] | None,
        account_id: str | None,
        case_id: str | None = None,
    ) -> AnalysisResponse:
        """Execute full Tier 1 + 2 + 3 verification for standalone Fraud Shield uploads."""
        if not files and not extracted_data:
            raise ValidationError("Provide at least one file or extracted_data JSON.")

        settings = get_settings()
        analysis_id = new_id("frd")
        effective_case = case_id or new_id("case")
        findings: list[FraudFinding] = []
        generated: list[ArtifactRef] = []
        evidence_bytes: list[bytes] = []

        if extracted_data:
            findings.extend(analyze_cross_field_logic(extracted_data))

        for idx, (file_name, raw, mime_type) in enumerate(files):
            if not raw:
                raise ValidationError(f"{file_name} is empty.")
            if len(raw) > settings.max_upload_bytes:
                raise ValidationError(f"{file_name} exceeds maximum upload size.")
            sha = hashlib.sha256(raw).hexdigest()
            ref = ArtifactRef(
                artifact_id=new_id("src"),
                module="fraud",
                kind="source_document",
                storage_key=f"fraud/{analysis_id}/source-{idx}-{file_name}",
                sha256=sha,
                mime_type=mime_type,
                byte_size=len(raw),
            )
            f_t1, a_t1 = await self._run_tier1_for_blob(
                analysis_id=analysis_id,
                case_id=effective_case,
                account_id=account_id,
                data=raw,
                mime_type=mime_type,
                sha256_hex=sha,
                evidence_bytes=evidence_bytes,
            )
            findings.extend(f_t1)
            generated.extend(a_t1)

            f_t3, a_t3 = await self._run_tier3_for_blob(
                analysis_id=analysis_id,
                artifact_ref=ref,
                data=raw,
                evidence_bytes=evidence_bytes,
            )
            findings.extend(f_t3)
            generated.extend(a_t3)

        explanation = await self._maybe_explain(findings, evidence_bytes)
        score, severity, short_circuit, four_eyes = compute_risk_summary(
            findings,
            short_circuit_threshold=settings.short_circuit_score_threshold,
            four_eyes_threshold=settings.four_eyes_score_threshold,
        )
        return await self._store.save_analysis(
            analysis_id=analysis_id,
            case_id=effective_case,
            account_id=account_id,
            mode="standalone",
            risk_score=score,
            severity=severity,
            short_circuit_recommended=short_circuit,
            requires_four_eyes=four_eyes,
            findings=findings,
            generated_artifacts=generated,
            explanation=explanation,
        )

    async def get_analysis(
        self,
        analysis_id: str,
        *,
        account_id: str | None,
    ) -> AnalysisResponse:
        """Retrieve a Fraud Shield analysis scoped to ``account_id``."""
        record = await self._store.get_analysis(analysis_id, account=account_id)
        if record is None:
            raise NotFoundError(f"Analysis {analysis_id} was not found.")
        return record

    async def get_artifact_bytes(
        self,
        analysis_id: str,
        artifact_id: str,
        *,
        account_id: str | None,
    ) -> tuple[bytes, str]:
        """Download a generated forensic heatmap/diff artifact belonging to ``analysis_id``."""
        record = await self.get_analysis(analysis_id, account_id=account_id)
        target = next((a for a in record.generated_artifacts if a.artifact_id == artifact_id), None)
        if target is None:
            raise NotFoundError(f"Artifact {artifact_id} was not found.")
        return await self._storage.get_bytes(target.storage_key), target.mime_type
