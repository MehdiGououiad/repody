# Research scripts (not product)

Experimental OCR / Structure / LLM tooling. Safe to ignore for production.

| Script | Purpose |
|--------|---------|
| `paddleocr-structure-v3-serve.mjs` | Local PP-StructureV3 serve helper |
| `qwen35-serve.mjs` | Qwen3.5-4B text→JSON arm |
| `nuextract2-serve.mjs` | NuExtract-2.0-2B IE arm |
| `run-cnie-json-compare.mjs` | Sequential CNIE JSON compare driver |

Config dirs: `deploy/research/qwen35/`, `deploy/research/nuextract2/`  
Backend benches: `backend/scripts/research/`  
Docs: [docs/experiments/CNIE-STRUCTURE-LLM.md](../../../docs/experiments/CNIE-STRUCTURE-LLM.md)
