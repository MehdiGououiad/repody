# llama-server for Repody: NuExtract3

NuExtract3 runs locally on the official **llama-server** binary (`winget install llama.cpp`), on an
OpenAI-compatible port. Platform wiring: `docs/EXTRACTION.md`.

No GPU on the server? Run the full NuExtract3 on vLLM on Modal, scaling to zero, inside the free tier:
[`deploy/modal/README.md`](../modal/README.md).

| Model      | Used for                      | Port | Weights                                                                 |
| ---------- | ----------------------------- | ---- | ----------------------------------------------------------------------- |
| NuExtract3 | Field extraction and Markdown | 8081 | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) |

## 1. Install llama.cpp

```powershell
winget install llama.cpp
# later: winget upgrade ggml.llamacpp   # latest GitHub Vulkan release
```

`llama-server --list-devices` lists the GPUs; llama.cpp uses one by default.

## 2. NuExtract3 weights

| File                          | Size                        |
| ----------------------------- | --------------------------- |
| `NuExtract3-Q8_0.gguf`        | ~4.6 GB                     |
| `NuExtract3-Q6_K.gguf`        | ~3.5 GB                     |
| `NuExtract3-Q4_K_M.gguf`      | ~2.7 GB                     |
| `mmproj-NuExtract3-BF16.gguf` | vision projector (required) |

`node deploy/scripts/llama-serve.mjs download` fetches the repository into `deploy/llamacpp/models`.
On the Repody OCR benchmark (`benchmarks/ocr`), Q8_0 is the most accurate.

## 3. Configure and start

```powershell
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
bun run llamacpp:serve
bun run llamacpp:verify
```

### Server flags

The launcher (`deploy/scripts/llama-serve.mjs`) passes only what the model card and llama.cpp need:

| Flag                                    | Why                                                                                                                                                    |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `-m` + `--mmproj` (or `-hf repo:quant`) | The weights and vision projector                                                                                                                       |
| `-a <alias>`                            | The model id Repody sends (`AUDIT_INFERENCE_MODEL`)                                                                                                    |
| `--jinja`                               | The chat template reads `chat_template_kwargs` (`template`, `mode`, thinking off)                                                                      |
| `-c` (`LLAMACPP_CONTEXT`) `-np 1`       | One request at a time with a 32768-token context (all pages in one request)                                                                            |
| `--image-min-tokens 1024`               | llama.cpp's advice for this model's accuracy: small images (a cropped ID card) get enough vision tokens to read their text; larger pages are unchanged |

Batch sizes, flash attention and GPU offload are llama.cpp's defaults. Repody sends
the images the model card describes (PDF pages at 170 DPI, as PNG), and every request sets the
documented sampling.

## 4. Point Repody at the server

```powershell
# backend/.env: AUDIT_INFERENCE_BASE_URL=http://127.0.0.1:8081/v1 (Compose: host.docker.internal)
docker compose --env-file backend/.env --profile workers restart worker
```

See `deploy/llamacpp/repody-llamacpp.env.example`.

## Manual commands

```powershell
llama-server -m C:\path\to\NuExtract3-Q8_0.gguf --mmproj C:\path\to\mmproj-NuExtract3-BF16.gguf `
  --host 0.0.0.0 --port 8081 -a nuextract3-q8_0 --jinja -c 32768 -np 1 --image-min-tokens 1024
```

## Throughput (`-np`)

Each slot gets its own context window. Match `LLAMACPP_PARALLEL` to the worker concurrency
(`AUDIT_WORKER_CONCURRENCY`, Helm `worker.concurrency`): runs beyond it wait in the queue.

```powershell
bun run llamacpp:restart
docker compose --env-file backend/.env --profile workers restart worker
```

## Troubleshooting

| Symptom                                   | Fix                                                                                 |
| ----------------------------------------- | ----------------------------------------------------------------------------------- |
| Slow first request                        | The first image also loads the vision projector                                     |
| `/v1/models` has no multimodal capability | Check the `LLAMACPP_MMPROJ` path                                                    |
| Model alias mismatch                      | Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_INFERENCE_MODEL`                           |
| Vulkan `ErrorDeviceLost` on large pages   | Update llama.cpp (`winget upgrade ggml.llamacpp`); report it upstream with the page |

Logs: `deploy/llamacpp/logs/` (`<model>-llama-server.*.log`).
