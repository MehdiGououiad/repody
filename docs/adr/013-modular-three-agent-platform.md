# ADR 013: Modular three-agent sovereign enterprise architecture

Extends [ADR 004](./004-cloud-kubernetes-packaging.md),
[ADR 010](./010-explicit-lifecycles.md), and [ADR 011](./011-hatchet.md).

## Context

Repody started as a single document-audit application (`repody-backend` + `repody-web` + single
Postgres database) hardwired around `Workflow -> Run -> RunDocument`. Selling into regulated
banking, insurance, and telecom environments on-premises requires:

1. Three independently sellable and deployable product modules — **IDP Agent**, **Fraud Shield
   Agent**, and **Computer-Use Operator** (Phase 2) — plus a domain-agnostic **Core Spine** so
   document-less browser jobs and standalone fraud APIs are first-class citizens.
2. Strict service, database, and UI isolation so unpurchased modules are neither deployed nor
   referenced in single-module installs, while multi-module installs chain seamlessly across a
   shared `Case` with Four-Eyes (Maker-Checker) approval gates.
3. 100% air-gap readiness, strictly permissive open-source licenses (`MIT`, `Apache-2.0`, `BSD`,
   `MPL-2.0`, `CC-BY-4.0` weights with attribution; zero `AGPL`, `GPL`, or `NC` dependencies), and
   swappable ports behind versioned contracts.

## Decision

### 1. Core Spine + Three Isolated Services

- **`repody-core`** (always deployed; DB `repody_core`): offline Ed25519 entitlements, `Case` /
  `Artifact` registry (supporting pure-JSON payloads with zero documents), Hatchet durable
  pipeline orchestration, Four-Eyes Maker-Checker approvals (`checker_sub <> maker_sub`),
  immutable `field_overrides`, hash-chained `audit_events`, and generalized `usage_entries`.
- **`repody-idp`** (DB `repody_idp`, Hatchet `pool=idp`): document extraction (`NuExtract3`) and
  validation workflows, callable standalone or as a Hatchet child workflow.
- **`repody-fraud`** (DB `repody_fraud` + `pgvector`, Hatchet `pool=fraud-cpu` / `pool=fraud-gpu`):
  standalone REST API and Hatchet pre-check/post-verify workflows using commercially safe SOTA
  libraries (`pyHanko`, `pikepdf`, `pypdfium2`, `ImageHash` + `pgvector`, `PhotoHolmes` Apache-2.0
  with `CAT-Net v2` + classical detectors, and `Mesorch` MIT). `PyMuPDF` (`AGPL-3.0`), `TruFor`
  (`NC`), `DocTamper` (`NC`), and `MVSS-Net` (`NC`) are explicitly excluded. `NuExtract3` remains
  focused on structured JSON/Markdown extraction and optional cropped hotspot re-OCR, while
  free-form visual anomaly commentary sits behind the swappable `VisualExplainer` protocol (off by
  default; swappable to `Qwen3-VL` Apache-2.0).
- **`repody-operator`** (Phase 2; DB `repody_operator`, Hatchet `pool=browser`): sandboxed web
  automation with cached deterministic replay and VLM self-healing.

By default each service uses its own logical database and credentials on Postgres, with Helm
overrides allowing physically separate Postgres clusters per service for Tier-1 banks.

### 2. Orchestration & Licensing

- **Hatchet** remains the sole async orchestration plane: `@hatchet.durable_task()` +
  `ctx.aio_wait_for(UserEventCondition(...))` for multi-module pipelines and long-running
  Four-Eyes pauses; DAG workflows for intra-module parallel steps; `desired_worker_labels` to pin
  CPU/GPU/browser pools; and `retries=0` + `NonRetryableError` for irreversible commit actions.
- **Dual-defense licensing:** Helm subcharts / Compose profiles exclude unpurchased containers
  completely, backed by an offline Ed25519 JWT (`repody_common.entitlements`) with a 30-day soft
  grace period so contract expiry emits warnings without halting live regulated operations.

### 3. Frontend Modularity & Strangler-Fig Migration

- Feature modules live under `modules/<name>` (`modules/core`, `modules/idp`, `modules/fraud`,
  `modules/pipelines`, later `modules/operator`) with Oxlint `no-restricted-imports` preventing
  cross-module coupling.
- Single-module entitlements bypass `/hub` and land directly inside the licensed workspace;
  multi-module entitlements open `/hub`, pipelines, and the unified Four-Eyes Case Inspector.
- `packages/repody-common` is developed in a root `uv` workspace excluding legacy `backend/` until
  Phase 1B completes extraction, keeping existing `backend/` CI and Dockerfiles green throughout.

## Consequences

- Every cross-service call uses versioned Pydantic schemas in `packages/repody-common` or OpenAPI
  HTTP contracts — zero shared database tables.
- Swapping an extraction model, tampering detector, visual explainer, or browser engine requires
  implementing its `Protocol` adapter without touching `repody-core` or the UI shell.
