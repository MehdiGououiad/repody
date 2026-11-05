#!/usr/bin/env bash
# NuExtract3, LightOnOCR-3-4B, Surya 2.5 and MinerU 4 on the real French documents, each set up as its
# documentation says, all on the Arc GPU through llama.cpp's Vulkan backend. One model at a time.
#   MODELS=/c/Users/Mehdi/OneDrive/Desktop/projects/agentcontrol/deploy/llamacpp/models bash run_vulkan4.sh
set -u
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)
MODELS=${MODELS:-/c/Users/Mehdi/OneDrive/Desktop/projects/agentcontrol/deploy/llamacpp/models}  # the weights live in the main checkout
PAGES=$(ls docs | grep '__real\.png$' | sed 's/\.png$//')
export HF_HUB_DISABLE_SYMLINKS_WARNING=1

wait_for() { until curl -sf "$1" > /dev/null; do sleep 2; done; }
stop_llama() { taskkill //F //IM llama-server.exe > /dev/null 2>&1 || true; sleep 2; }

(cd "$ROOT" && pnpm -s llamacpp:stop > /dev/null 2>&1); stop_llama

echo "== NuExtract3 Q8_0 (llama.cpp defaults; the card's Markdown request)"
llama-server -m "$MODELS/NuExtract3-Q8_0.gguf" --mmproj "$MODELS/mmproj-NuExtract3-BF16.gguf" \
  --port 8081 --alias nuextract3-q8_0 --jinja > outputs/nuextract3-docs-server.log 2>&1 &
wait_for http://127.0.0.1:8081/health
BENCH_NAME=nuextract3-q8_0-defaults BENCH_RUNTIME="llama.cpp b12098 Vulkan, Q8_0, default server flags" \
  uv run runners/nuextract3.py $PAGES
stop_llama

echo "== LightOnOCR-3-4B Q8_0 (prithivMLmods GGUF card; LightOnOCR-3 request settings)"
llama-server -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q8_0 --port 18501 --jinja > outputs/lightonocr-q8-server.log 2>&1 &
wait_for http://127.0.0.1:18501/health
LIGHTON_QUANT=Q8_0 uv run runners/lightonocr_gguf.py $PAGES
stop_llama

echo "== Surya OCR 2.5 (surya-ocr spawns the Vulkan llama-server)"
uv run runners/surya_ocr.py $PAGES
stop_llama

echo "== MinerU 4 standard, Markdown"
MINERU_FORMAT=markdown uv run runners/mineru.py $PAGES
echo "== MinerU 4 standard, middle_json"
MINERU_FORMAT=middle_json uv run runners/mineru.py $PAGES

(cd "$ROOT" && pnpm -s llamacpp:serve > /dev/null 2>&1)
uv run score.py
echo "== done"
