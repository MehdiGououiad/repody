#!/usr/bin/env bash
# Pull + package Repody VLM for Docker Model Runner.
# Constants synced with deploy/repody-vlm-model.constants.mjs
set -euo pipefail

PULL_SOURCE="hf.co/numind/NuExtract3-GGUF:Q4_K_M"
PACKAGE_FROM="huggingface.co/numind/nuextract3-gguf:Q4_K_M"
TARGET="${AUDIT_REPODY_VLM_MODEL:-repody/repody-vlm:q4_k_m-16k}"

if docker model inspect "$TARGET" >/dev/null 2>&1; then
  echo "Repody VLM model ready: $TARGET" >&2
  exit 0
fi

echo "Pulling Repody VLM weights (first run only; may take a few minutes)…" >&2
docker model pull "$PULL_SOURCE"
docker model package --from "$PACKAGE_FROM" --context-size 16384 "$TARGET"
echo "Repody VLM ready: $TARGET" >&2
