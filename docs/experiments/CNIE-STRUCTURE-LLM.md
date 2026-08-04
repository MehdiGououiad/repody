# Experiment: CNIE StructureV3 vs PP-OCRv6 + LLM (JSON compare)

Bench-only comparison on the Gououiad Moroccan CNIE fixture (`gououiad-cnie-{front,back}.png`).

**What we compare:** the **same CNIE schema JSON** produced by Qwen3.5-4B from two text sources:

| Path | Text source | JSON |
|---|---|---|
| `ocr-llm` | PP-OCRv6 `POST /ocr` (front + back) | Qwen text→JSON |
| `structure-llm` | PP-StructureV3 `POST /layout-parsing` markdown | Qwen text→JSON |

Both JSON objects are scored with `score_gououiad_cnie_fields` and written side-by-side.

## Official docs

- PP-StructureV3: https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PP-StructureV3.html
- Serving contract: `paddlex --serve --pipeline PP-StructureV3` → **`POST /layout-parsing`** `{ file, fileType }` → `result.layoutParsingResults[].markdown.text`
- PP-OCRv6: `POST /ocr` `{ file, fileType }`
- Qwen3.5-4B GGUF: https://huggingface.co/unsloth/Qwen3.5-4B-GGUF

## Sequential run (required — no parallel models)

Experimental tooling (not first-class `package.json` scripts). From repo root:

```powershell
pnpm paddleocr:v6:serve   # auto-installs deps if needed, then leave running
node deploy/scripts/research/paddleocr-structure-v3-serve.mjs install
copy deploy\research\qwen35\paths.local.env.example deploy\research\qwen35\paths.local.env

node deploy/scripts/research/run-cnie-json-compare.mjs
```

That script:

1. Kills OCR / Structure / Qwen / GLM / NuExtract
2. Starts **only** PP-OCRv6 → runs front+back OCR → stops OCR
3. Starts **only** PP-StructureV3 → runs front+back layout → stops Structure
4. Starts **only** Qwen → builds JSON from both texts → stops Qwen

Reports under `benchmark-reports/cnie-structure-llm/<stamp>/`:

- `report.md` — field scores + side-by-side JSON table
- `ocr-llm.fields.json` / `structure-llm.fields.json` — raw JSON fields
- `report.json` — full timings + markdown samples
