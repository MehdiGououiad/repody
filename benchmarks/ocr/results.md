# OCR benchmark (30 pages)

| Model | Score | Values | Lines | Tables | Digital | Scan | Low-res | Photo | Fax | Payslip | s/page | Missing | Runtime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nuextract3-q8_0 | **99.2** | 98.9 | 99.1 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | 86.9 | 38.1 | 0 | llama.cpp b12098 Vulkan, Q8_0 |
| surya-ocr-2.5 | **98.2** | 97.8 | 100.0 | 95.1 | 100.0 | 100.0 | 100.0 | 100.0 | 97.1 | 53.5 | 23.6 | 0 | surya-ocr, llama.cpp b12098 Vulkan (auto-spawned) |
| minicpm-ocr-1.0 | **94.3** | 94.6 | 97.3 | 90.9 | 100.0 | 100.0 | 100.0 | 83.2 | 84.2 | 61.7 | 40.2 | 0 | minicpm-ocr SDK (layout CPU) + llama.cpp b12098 Vulkan, Q8_0 |
