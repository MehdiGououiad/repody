#!/usr/bin/env bash
# NuExtract3 Markdown through Repody's own pipeline, on the server started by the Repody launcher.
set -u
cd "$(dirname "$0")/../.."
taskkill //F //IM llama-server.exe > /dev/null 2>&1; sleep 2
echo "== NuExtract3 via Repody (bun run llamacpp:serve)"
node deploy/scripts/llama-serve.mjs serve nuextract | grep -E "args:|is up|OK|NOT READY"
(cd backend && uv run python ../benchmarks/ocr/via_repody.py)
echo "== done"
