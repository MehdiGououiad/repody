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
