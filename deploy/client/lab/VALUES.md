# Lab Helm values matrix

Canonical lab overlays under `deploy/client/lab/`. Merge onto a promoted base (see [OPENSHIFT.md](../../../docs/deploy/OPENSHIFT.md)).

## Base profiles (pick one)

| File | When |
|------|------|
| `values.lab.common.yaml` | Shared lab knobs |
| `values.lab.bundled.yaml` | Bundled Postgres/Redis/MinIO |
| `values.lab.external.yaml` | External data plane |
| `values.openshift-local.yaml` | CRC / local OpenShift defaults |
| `values.data.openshift-local.yaml` | Data chart local overrides |
| `values.auth.openshift-local.yaml` | Auth chart local overrides |

## Promoted / CRC snapshots

| File | When |
|------|------|
| `values.openshift-local.promoted.yaml` | Last known-good promoted app values |
| `values.openshift-local.crc.yaml` | CRC-tuned app values |
| `values.auth.openshift-local.promoted.yaml` | Promoted auth values |

## Stress / scale overlays (merge last)

| File | When |
|------|------|
| `values.stress-test.yaml` | Multi-node stress (`pnpm stress:prod`) |
| `values.stress-test.crc.yaml` | Single-node CRC stress |
| `values.cpu-scale.yaml` | HPA / CPU scale experiments |
| `values.cpu-scale.crc.yaml` | CRC manual replica/CPU tuning |

Do not invent parallel “local” files — extend this matrix or update the matching row.
