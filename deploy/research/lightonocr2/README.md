# LightOnOCR-2 GGUF (research)

Official model: [lightonai/LightOnOCR-2-1B](https://huggingface.co/lightonai/LightOnOCR-2-1B)

- **Official serve:** vLLM / Transformers (image-only chat, PDF **200 DPI**, longest side **1540px**, `temperature=0.2`, `top_p=0.9`)
- **GGUF (author):** [staghado/LightOnOCR-2-1B-Q8_0-GGUF](https://huggingface.co/staghado/LightOnOCR-2-1B-Q8_0-GGUF) — requires **latest llama.cpp main**

```powershell
llama-server -hf staghado/LightOnOCR-2-1B-Q8_0-GGUF -c 8192 --temp 0.2 --top-k 0 --top-p 0.9 --port 8090
```

## Local result (2026-08-06)

Winget `llama-server` **b10155** + staghado Q8_0 (+ wangjazz F16 mmproj) → **broken**: endless Japanese `気に` loop, no usable OCR. Not a quant issue — same with image-only / `OCR` / `OCR markdown` prompts.

**Next official paths to try:** upgrade llama.cpp to current main, or run BF16 via `vllm serve lightonai/LightOnOCR-2-1B`.
