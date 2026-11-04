#!/usr/bin/env bash
# MiniCPM-OCR 1.0 with DSpark speculative decoding, served as in the official llama.cpp guide
# (docs/llamacpp_deploy.md in OpenBMB/MiniCPM-OCR), then scored.
#   MODELS=/c/Users/Mehdi/models/ocr-bench bash run_dspark.sh
set -u
cd "$(dirname "$0")"
M=${MODELS:-$HOME/models/ocr-bench}/minicpm-ocr-1.0
"${LLAMA_SERVER:-llama-server}" --model "$M/MiniCPM-OCR-1_0-Q8_0.gguf" --mmproj "$M/mmproj-model-f16-4x.gguf" \
  --model-draft "$M/dspark-MiniCPM-OCR-1_0-Q8_0.gguf" --spec-type draft-dspark --spec-draft-n-max 15 \
  --n-gpu-layers 99 --gpu-layers-draft 99 --flash-attn on --ctx-size 8192 --parallel 1 \
  --host 127.0.0.1 --port 18499 --alias minicpm-ocr --jinja --reasoning off \
  > outputs/minicpm-dspark-llama-server.log 2>&1 &
SERVER=$!
until curl -sf http://127.0.0.1:18499/health > /dev/null; do sleep 2; done
BENCH_VARIANT=dspark uv run runners/minicpm_ocr.py "$@"
kill $SERVER; wait $SERVER 2> /dev/null
uv run score.py
