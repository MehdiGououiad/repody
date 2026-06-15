#!/usr/bin/env bash
# Export Repody VLM Docker Model Runner artifact for air-gap bundles (Linux CI / staging).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${1:?output directory required}"
mkdir -p "$OUT_DIR"

# shellcheck source=/dev/null
source "${ROOT}/scripts/model-pull-repody-vlm.sh"

TARGET="${AUDIT_REPODY_VLM_MODEL:-repody/repody-vlm:q4_k_m-16k}"
ARCHIVE="${OUT_DIR}/repody-vlm-model.tar"

if docker save -o "$ARCHIVE" "$TARGET" 2>/dev/null; then
  echo "Exported model image archive: $ARCHIVE"
  exit 0
fi

# Docker Model Runner models may not be plain OCI images — ship metadata + pull source for internal HF mirror.
cat >"${OUT_DIR}/MODEL_INFO.json" <<EOF
{
  "type": "docker-model-runner",
  "target": "${TARGET}",
  "pullSource": "hf.co/numind/NuExtract3-GGUF:Q4_K_M",
  "packageFrom": "huggingface.co/numind/nuextract3-gguf:Q4_K_M",
  "note": "Import host must run: docker model pull <internal-mirror-of-pullSource> && docker model package --from <internal-mirror-of-packageFrom> --context-size 16384 ${TARGET}"
}
EOF
echo "Model is not docker-save compatible; wrote ${OUT_DIR}/MODEL_INFO.json" >&2
echo "Mirror Hugging Face GGUF to an internal registry and import on the regulated host." >&2
exit 0
