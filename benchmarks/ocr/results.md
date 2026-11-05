# OCR benchmark (37 pages)

Ranked by the lenient score (decimal comma = point). Component and variant columns are lenient.

| Model | Lenient | Strict | Values | Lines | Tables | Digital | Scan | Low-res | Photo | Fax | Real | s/page | Missing | Runtime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| surya-ocr-2.5 | **83.5** | 82.3 | 83.1 | 83.8 | 90.9 | 100.0 | 100.0 | 100.0 | 100.0 | 97.1 | 24.6 | 23.5 | 6 | surya-ocr, llama.cpp b12098 Vulkan (auto-spawned) |
| nuextract3-q8_0 | **83.1** | 83.1 | 82.7 | 83.0 | 90.9 | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | 23.2 | 41.2 | 6 | llama.cpp b12098 Vulkan, Q8_0 |
| minicpm-ocr-1.0 | **80.1** | 79.1 | 80.2 | 81.4 | 87.0 | 100.0 | 100.0 | 100.0 | 83.2 | 84.6 | 24.4 | 40.2 | 6 | minicpm-ocr SDK (layout CPU) + llama.cpp b12098 Vulkan, Q8_0 |
| lightonocr-3-4b-q4_k_m | **2.7** | 2.7 | 2.6 | 2.7 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.3 | 52.8 | 36 | llama.cpp b12098 Vulkan, Q4_K_M (prithivMLmods GGUF) |
| mineru-4-standard | **2.6** | 2.6 | 2.6 | 2.6 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.1 | 19.3 | 36 | mineru-kit 4.x --tier standard (ONNX + llama.cpp) |
| glm-ocr | **2.6** | 2.6 | 2.6 | 2.5 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 11.9 | 38.4 | 36 | glmocr SDK (layout CPU) + Ollama 0.40 glm-ocr:latest |

## Real documents (lenient)

| Page | surya-ocr-2.5 | nuextract3-q8_0 | minicpm-ocr-1.0 | lightonocr-3-4b-q4_k_m | mineru-4-standard | glm-ocr |
|---|---|---|---|---|---|---|
| asiahome__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| babani__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| canda__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| espacetransit__real | 98.5 | 98.5 | 95.6 | 98.5 | 97.0 | 95.6 |
| fiche__real | 98.4 | 86.9 | 99.2 | 0.0 | 0.0 | 0.0 |
| quittance1968__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| retouche__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vigan__real | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
