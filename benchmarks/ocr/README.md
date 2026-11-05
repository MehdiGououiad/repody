# OCR benchmark

Document OCR models on the documents Repody audits, run on this machine (Intel Core Ultra 7 258V,
Arc 140V iGPU, 32 GB) with each model's **official** inference path.

## Pages (30)

- `make_docs.py`: 8 French/English business documents with known content (invoices, a 22-line invoice,
  purchase order, bank statements incl. a 30-row unruled one, receipt, form, contract), each as a
  digital PDF and as degraded copies: scan (200 DPI, tilt, noise, JPEG), low-res (110 DPI), phone
  photo (perspective, uneven light, blur, JPEG 40) and fax (100 DPI black and white).
- `real_docs.py`: the real payslip `e2e/fixtures/documents/fiche.webp` with a hand-written gold.

## Score (`score.py`)

Per page: **values** (amounts, ids, dates, IBANs found exactly, spaces and case ignored), **lines**
(text lines, fuzzy >= 90), **tables** (each row found as one output row with every cell). The page
score is their mean; the model score is the mean over pages. Speed is the median seconds per page.

## Runners (official ways only)

| Model | Runner | Path |
|---|---|---|
| NuExtract3 Q8_0 | `runners/nuextract3.py` | llama.cpp (Vulkan), Markdown mode, as Repody calls it |
| MiniCPM-OCR 1.0 | `runners/minicpm_ocr.py` | official SDK (PP-DocLayoutV3 on CPU) + llama.cpp service per the GGUF card |
| Surya OCR 2.5 | `runners/surya_ocr.py` | `surya-ocr` with its llama.cpp backend (auto-spawned server) |

Not run: OXR-1.0, Unlimited-OCR-2 and Nemotron 3.5 Parse (official paths are NVIDIA-only), and
LightOnOCR-3-4B and Xiaomi-OCR-0 (official path here is CPU Transformers; dropped as too slow).

    uv run make_docs.py && uv run real_docs.py
    pnpm llamacpp:serve && uv run runners/nuextract3.py      # then pnpm llamacpp:stop
    MODELS=~/models/ocr-bench bash run_others.sh            # MiniCPM, Surya, then score.py
    MODELS=~/models/ocr-bench bash run_dspark.sh            # MiniCPM with its DSpark draft head

## Results (2026-11-04, llama.cpp b12098)

| Model | Score | Values | Lines | Tables | Digital | Scan | Low-res | Photo | Fax | Payslip | s/page |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NuExtract3 Q8_0 | **99.2** | 98.9 | 99.1 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | 86.9 | 38.1 |
| Surya OCR 2.5 | **98.2** | 97.8 | 100.0 | 95.1 | 100.0 | 100.0 | 100.0 | 100.0 | 97.1 | 53.5 | 23.6 |
| MiniCPM-OCR 1.0 | **94.3** | 94.6 | 97.3 | 90.9 | 100.0 | 100.0 | 100.0 | 83.2 | 84.2 | 61.7 | 40.2 |

On the payslip, Surya and MiniCPM write the French decimal comma as a point (`3 500.00€` for
`3 500,00€`), which the exact score counts as wrong. Treating `,` and `.` as equal, the payslip scores
are Surya 98.4, MiniCPM 99.2 and NuExtract3 86.9 (NuExtract3 misread the URSSAF number and the
hourly rate, and left out the employee block).

### MiniCPM-OCR DSpark (speculative decoding)

`run_dspark.sh` serves MiniCPM-OCR with the `MiniCPM-OCR-1.0-DSpark-gguf` draft head exactly as the
official llama.cpp guide. On this machine's Vulkan backend llama-server aborts on the first request
(`ggml-vulkan.cpp:5779: GGML_ASSERT(allow_misalign || misalign_bytes == 0)`) with both b12098 and
b12119, so there is no DSpark result yet. The guide was verified on Metal; CUDA is also documented.
Rerun the script (`LLAMA_SERVER=<path>` picks a build) once llama.cpp fixes it.

## Real French documents, all on the Arc GPU (2026-11-05)

Eight real documents with hand-checked gold (`real_docs.py`): a payslip, a hand-filled repair invoice,
a handwritten invoice, a dense Moroccan customs invoice, a faded 1981 till receipt, a 1968 rent
receipt, a 1921 invoice and an 1832 delivery note. Each model as its documentation sets it up, on the
Arc 140V through llama.cpp's Vulkan backend (`run_vulkan4.sh`, `rerun_nuextract.sh`). Lenient score.

| Model | Mean | Asia Home | Babani 1921 | C&A 1981 | Espace Transit | Payslip | Rent 1968 | Retouche | Vigan 1832 | s/page |
|---|---|---|---|---|---|---|---|---|---|---|
| NuExtract3 Q8_0, llama.cpp default flags | **96.9** | 89 | 98 | 100 | 99 | 100 | 97 | 100 | 92 | 105 |
| LightOnOCR-3-4B Q8_0 (prithivMLmods GGUF) | 93.2 | 88 | 67 | 100 | 100 | 99 | 100 | 100 | 92 | 62 |
| Surya OCR 2.5 | 87.6 | 89 | 84 | 100 | 98 | 98 | 59 | 100 | 72 | 30 |
| MinerU 4 standard, middle_json | 75.1 | 43 | 62 | 75 | 97 | 97 | 62 | 100 | 64 | 29 |
| MinerU 4 standard, Markdown | 68.9 | 43 | 32 | 75 | 78 | 97 | 62 | 100 | 64 | 31 |

- NuExtract3 with llama.cpp's default server flags scores 100 on the payslip; with Repody's server flags
  (`--image-min/max-tokens 1024`, `-ub 1024`, ...) it scored 86.9 there and took longer.
- LightOnOCR Q8_0 fixes the Q4_K_M misread on the customs invoice and reads old cursive well; it drops
  part of the 1921 invoice (Babani 67).
- Surya is the fastest whole-page model but weak on cursive handwriting (rent receipt 59, 1832 note 72).
- MinerU reads printed pages well but handwriting poorly (Asia Home 43); its Markdown also leaves out
  headers and footers, which `middle_json` keeps.

`real_scores.py` prints this table from the outputs.

### Through Repody's own pipeline (2026-11-05)

`run_via_repody.sh` starts both servers with Repody's launcher (`deploy/scripts/llama-serve.mjs`:
llama.cpp defaults, no image-token cap) and sends the eight real documents through
`repody.extraction.pipeline.extract` in Markdown mode (`via_repody.py`):

| Path | Mean | Asia Home | Babani | C&A | Espace Transit | Payslip | Rent 1968 | Retouche | Vigan |
|---|---|---|---|---|---|---|---|---|---|
| Repody, `AUDIT_MARKDOWN_PROVIDER=nuextract` | **96.9** | 89 | 98 | 100 | 99 | 100 | 97 | 100 | 92 |
| Repody, `AUDIT_MARKDOWN_PROVIDER=lightonocr` | **92.8** | 88 | 67 | 100 | 97 | 99 | 100 | 100 | 92 |

NuExtract3's output is byte-for-byte the benchmark run's. LightOnOCR samples (temperature 0.2), so a
run differs slightly: here it misread `CASOI21005079` as `CASO1…` on the customs invoice.
