#!/usr/bin/env bash
# NuExtract3 alone on the real documents, llama.cpp defaults (the same setup as run_vulkan4.sh).
set -u
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
MODELS=${MODELS:-/c/Users/Mehdi/OneDrive/Desktop/projects/agentcontrol/deploy/llamacpp/models}
PAGES=$(ls docs | grep '__real\.png$' | sed 's/\.png$//')
(cd "$ROOT" && pnpm -s llamacpp:stop > /dev/null 2>&1); taskkill //F //IM llama-server.exe > /dev/null 2>&1; sleep 2
rm -rf outputs/nuextract3-q8_0-defaults
echo "== NuExtract3 Q8_0 rerun (llama.cpp defaults)"
llama-server -m "$MODELS/NuExtract3-Q8_0.gguf" --mmproj "$MODELS/mmproj-NuExtract3-BF16.gguf" \
  --port 8081 --alias nuextract3-q8_0 --jinja > outputs/nuextract3-docs-server.log 2>&1 &
until curl -sf http://127.0.0.1:8081/health > /dev/null; do sleep 2; done
BENCH_NAME=nuextract3-q8_0-defaults BENCH_RUNTIME="llama.cpp b12098 Vulkan, Q8_0, default server flags" \
  uv run runners/nuextract3.py $PAGES
taskkill //F //IM llama-server.exe > /dev/null 2>&1; sleep 2
(cd "$ROOT" && pnpm -s llamacpp:serve > /dev/null 2>&1)
uv run score.py
echo "== done"
