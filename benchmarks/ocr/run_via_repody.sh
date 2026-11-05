#!/usr/bin/env bash
# Both Markdown providers through Repody's own pipeline, on servers started by the Repody launcher.
set -u
cd "$(dirname "$0")/../.."
taskkill //F //IM llama-server.exe > /dev/null 2>&1; sleep 2
echo "== NuExtract3 via Repody (pnpm llamacpp:serve)"
node deploy/scripts/llama-serve.mjs serve nuextract | grep -E "args:|is up|OK|NOT READY"
(cd backend && uv run python ../benchmarks/ocr/via_repody.py nuextract)
node deploy/scripts/llama-serve.mjs stop nuextract > /dev/null
echo "== LightOnOCR via Repody (pnpm lightonocr:serve)"
node deploy/scripts/llama-serve.mjs serve lightonocr | grep -E "args:|is up|OK|NOT READY"
(cd backend && uv run python ../benchmarks/ocr/via_repody.py lightonocr)
node deploy/scripts/llama-serve.mjs stop lightonocr > /dev/null
node deploy/scripts/llama-serve.mjs serve nuextract > /dev/null
echo "== done"
