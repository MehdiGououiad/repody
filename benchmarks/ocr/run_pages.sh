#!/usr/bin/env bash
# Run every model, one at a time, on the given pages only, then score.
#   MODELS=/c/Users/Mehdi/models/ocr-bench bash run_pages.sh espacetransit__real [more pages]
# Each model runs as its official guide sets it up (see the runners' docstrings).
set -u
cd "$(dirname "$0")"
MODELS=${MODELS:-$HOME/models/ocr-bench}
ROOT=$(cd ../.. && pwd)
PAGES=("$@")
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

wait_for() { until curl -sf "$1" > /dev/null; do sleep 2; done; }
stop_llama() { taskkill //F //IM llama-server.exe > /dev/null 2>&1 || true; sleep 2; }

echo "== NuExtract3 (Repody's llama-server)"
(cd "$ROOT" && pnpm -s llamacpp:serve > /dev/null 2>&1)
uv run runners/nuextract3.py "${PAGES[@]}"
(cd "$ROOT" && pnpm -s llamacpp:stop > /dev/null 2>&1); stop_llama

echo "== MiniCPM-OCR 1.0"
M="$MODELS/minicpm-ocr-1.0"
llama-server -m "$M/MiniCPM-OCR-1_0-Q8_0.gguf" --mmproj "$M/mmproj-model-f16-4x.gguf" --port 18499 \
  --alias minicpm-ocr --ctx-size 8192 --parallel 1 --jinja --reasoning off -ngl 99 > outputs/minicpm-server.log 2>&1 &
wait_for http://127.0.0.1:18499/health
uv run runners/minicpm_ocr.py "${PAGES[@]}"
stop_llama

echo "== Surya OCR 2.5"
uv run runners/surya_ocr.py "${PAGES[@]}"
stop_llama

echo "== LightOnOCR-3-4B GGUF Q4_K_M"
llama-server -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q4_K_M --port 18501 -ngl 99 --jinja > outputs/lightonocr-server.log 2>&1 &
wait_for http://127.0.0.1:18501/health
uv run runners/lightonocr_gguf.py "${PAGES[@]}"
stop_llama

echo "== GLM-OCR (Ollama)"
uv run runners/glm_ocr.py "${PAGES[@]}"
ollama stop glm-ocr:latest > /dev/null 2>&1

echo "== MinerU 4 standard"
uv run runners/mineru.py "${PAGES[@]}"

echo "== PaddleOCR-VL-1.6 (CPU)"
uv run runners/paddleocr_vl.py "${PAGES[@]}"

(cd "$ROOT" && pnpm -s llamacpp:serve > /dev/null 2>&1)
uv run score.py
