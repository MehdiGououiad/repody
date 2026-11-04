#!/usr/bin/env bash
# Run every non-NuExtract model, one at a time (nothing else loaded), then score.
#   MODELS=/c/Users/Mehdi/models/ocr-bench bash run_others.sh
set -u
cd "$(dirname "$0")"
MODELS=${MODELS:-$HOME/models/ocr-bench}

echo "== MiniCPM-OCR 1.0 (llama.cpp service as in openbmb/MiniCPM-OCR-1.0-gguf)"
llama-server -m "$MODELS/minicpm-ocr-1.0/MiniCPM-OCR-1_0-Q8_0.gguf" \
  --mmproj "$MODELS/minicpm-ocr-1.0/mmproj-model-f16-4x.gguf" \
  --port 18499 --alias minicpm-ocr --ctx-size 8192 --parallel 1 --jinja --reasoning off -ngl 99 \
  > outputs/minicpm-llama-server.log 2>&1 &
SERVER=$!
until curl -sf http://127.0.0.1:18499/health > /dev/null; do sleep 2; done
uv run runners/minicpm_ocr.py
kill $SERVER; wait $SERVER 2> /dev/null

echo "== Surya OCR 2.5 (spawns its own llama-server)"
uv run runners/surya_ocr.py
taskkill //F //IM llama-server.exe > /dev/null 2>&1  # Surya cannot stop its server on Windows

echo "== Xiaomi-OCR-0 (Transformers, CPU)"
uv run runners/xiaomi_ocr.py

uv run score.py
