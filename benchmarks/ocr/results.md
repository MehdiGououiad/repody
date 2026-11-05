# OCR benchmark (37 pages)

Ranked by the lenient score (decimal comma = point). Component and variant columns are lenient.

| Model | Lenient | Strict | Values | Lines | Tables | Digital | Scan | Low-res | Photo | Fax | Real | s/page | Missing | Runtime |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| surya-ocr-2.5 | **97.1** | 95.9 | 95.4 | 98.3 | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 97.1 | 87.6 | 23.5 | 0 | surya-ocr, llama.cpp b12098 Vulkan (auto-spawned) |
| nuextract3-q8_0 | **83.1** | 83.1 | 82.7 | 83.0 | 90.9 | 100.0 | 100.0 | 100.0 | 100.0 | 96.4 | 23.2 | 41.2 | 6 | llama.cpp b12098 Vulkan, Q8_0 |
| minicpm-ocr-1.0 | **80.1** | 79.1 | 80.2 | 81.4 | 87.0 | 100.0 | 100.0 | 100.0 | 83.2 | 84.6 | 24.4 | 40.2 | 6 | minicpm-ocr SDK (layout CPU) + llama.cpp b12098 Vulkan, Q8_0 |
| nuextract3-q8_0-defaults | **20.9** | 20.9 | 21.3 | 20.5 | 17.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 96.9 | 97.3 | 29 | llama.cpp b12098 Vulkan, Q8_0, default server flags |
| lightonocr-3-4b-q8_0 | **20.2** | 20.2 | 20.9 | 21.2 | 13.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 93.2 | 60.0 | 29 | llama.cpp b12098 Vulkan, Q8_0 (prithivMLmods GGUF) |
| mineru-4-standard-middle_json | **16.2** | 16.2 | 18.2 | 15.8 | 13.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 75.1 | 28.1 | 29 | mineru-kit 4.1.7 --tier standard, middle_json (llama.cpp Vulkan + ONNX DirectML) |
| mineru-4-standard-markdown | **14.9** | 14.9 | 16.6 | 13.4 | 13.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 68.9 | 30.4 | 29 | mineru-kit 4.1.7 --tier standard, markdown (llama.cpp Vulkan + ONNX DirectML) |
| lightonocr-3-4b-q4_k_m | **2.7** | 2.7 | 2.6 | 2.7 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.3 | 52.8 | 36 | llama.cpp b12098 Vulkan, Q4_K_M (prithivMLmods GGUF) |
| mineru-4-standard | **2.6** | 2.6 | 2.6 | 2.6 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.1 | 19.3 | 36 | mineru-kit 4.x --tier standard (ONNX + llama.cpp) |
| glm-ocr | **2.6** | 2.6 | 2.6 | 2.5 | 4.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 11.9 | 38.4 | 36 | glmocr SDK (layout CPU) + Ollama 0.40 glm-ocr:latest |

## Real documents (lenient)

| Page | surya-ocr-2.5 | nuextract3-q8_0 | minicpm-ocr-1.0 | nuextract3-q8_0-defaults | lightonocr-3-4b-q8_0 | mineru-4-standard-middle_json | mineru-4-standard-markdown | lightonocr-3-4b-q4_k_m | mineru-4-standard | glm-ocr |
|---|---|---|---|---|---|---|---|---|---|---|
| asiahome__real | 89.2 | 0.0 | 0.0 | 89.2 | 87.5 | 43.2 | 43.2 | 0.0 | 0.0 | 0.0 |
| babani__real | 84.1 | 0.0 | 0.0 | 97.6 | 66.7 | 61.9 | 31.7 | 0.0 | 0.0 | 0.0 |
| canda__real | 100.0 | 0.0 | 0.0 | 100.0 | 100.0 | 75.0 | 75.0 | 0.0 | 0.0 | 0.0 |
| espacetransit__real | 98.5 | 98.5 | 95.6 | 98.6 | 100.0 | 97.0 | 77.8 | 98.5 | 97.0 | 95.6 |
| fiche__real | 98.4 | 86.9 | 99.2 | 100.0 | 99.2 | 97.3 | 97.3 | 0.0 | 0.0 | 0.0 |
| quittance1968__real | 58.8 | 0.0 | 0.0 | 97.4 | 100.0 | 62.3 | 62.3 | 0.0 | 0.0 | 0.0 |
| retouche__real | 100.0 | 0.0 | 0.0 | 100.0 | 100.0 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 |
| vigan__real | 71.8 | 0.0 | 0.0 | 92.3 | 92.3 | 64.1 | 64.1 | 0.0 | 0.0 | 0.0 |
