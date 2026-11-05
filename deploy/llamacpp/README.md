# llama-server for Repody: NuExtract3, and LightOnOCR-3 (optional)

Repody's models run on the official **llama-server** binary (`winget install llama.cpp`), each on its
own OpenAI-compatible port. Platform wiring: `docs/EXTRACTION.md`.

| Model | Used for | Port | Weights |
|---|---|---|---|
| NuExtract3 | Field extraction, and Markdown by default | 8081 | [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) |
| LightOnOCR-3-4B | Markdown when `AUDIT_MARKDOWN_PROVIDER=lightonocr` | 8082 | [prithivMLmods/LightOnOCR-3-4B-GGUF](https://huggingface.co/prithivMLmods/LightOnOCR-3-4B-GGUF) |

## 1. Install llama.cpp

```powershell
winget install llama.cpp
# later: winget upgrade ggml.llamacpp   # latest GitHub Vulkan release
```

`llama-server --list-devices` lists the GPUs; llama.cpp uses one by default.

## 2. NuExtract3 weights

| File | Size |
|------|------|
| `NuExtract3-Q8_0.gguf` | ~4.6 GB |
| `NuExtract3-Q6_K.gguf` | ~3.5 GB |
| `NuExtract3-Q4_K_M.gguf` | ~2.7 GB |
| `mmproj-NuExtract3-BF16.gguf` | vision projector (required) |

`node deploy/scripts/llama-serve.mjs download` fetches the repository into `deploy/llamacpp/models`.
On the Repody OCR benchmark (`benchmarks/ocr`), Q8_0 is the most accurate.

## 3. Configure and start

```powershell
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
pnpm llamacpp:serve
pnpm llamacpp:verify
```

### Server flags

The launcher (`deploy/scripts/llama-serve.mjs`) passes only what the model cards and llama.cpp need:

| Flag | Why |
|------|-----|
| `-m` + `--mmproj` (or `-hf repo:quant`) | The weights and vision projector |
| `-a <alias>` | The model id Repody sends (`AUDIT_*_SERVED_MODEL`) |
| `--jinja` | The chat templates read `chat_template_kwargs` (NuExtract `mode`/`template`, thinking off) |
| `-c` (`*_CONTEXT`) `-np 1` | One request at a time with its own context: 32768 for NuExtract (several pages per request), 16384 for LightOnOCR (one page per request) |
| `--reasoning off` | LightOnOCR only: the LightOnOCR-3 card serves with thinking off (vLLM `--default-chat-template-kwargs`) |

Image resolution, batch sizes, flash attention and GPU offload are llama.cpp's defaults. Repody sends
the images the model cards describe (NuExtract3: PDF pages at 170 DPI; LightOnOCR-3: at most 2048 px on
the longest edge), and every request sets the documented sampling.

## 4. Point Repody at the servers

```powershell
# backend/.env: AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1 (Compose: host.docker.internal)
docker compose --profile workers restart worker
```

See `deploy/llamacpp/repody-llamacpp.env.example`.

## LightOnOCR-3 for Markdown (optional)

Documents without fields are transcribed to Markdown. NuExtract3 does it by default; to use
LightOnOCR-3 instead:

```powershell
pnpm lightonocr:serve      # llama-server -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q8_0 on :8082
pnpm lightonocr:verify
```

Then set `AUDIT_MARKDOWN_PROVIDER=lightonocr` (and `AUDIT_LIGHTONOCR_BASE_URL` when it is not on
`127.0.0.1:8082`). The first start downloads the weights into llama.cpp's cache; set
`LIGHTONOCR_MODEL` and `LIGHTONOCR_MMPROJ` in `paths.local.env` to use local files instead.

## Manual commands

```powershell
llama-server -m C:\path\to\NuExtract3-Q8_0.gguf --mmproj C:\path\to\mmproj-NuExtract3-BF16.gguf `
  --host 0.0.0.0 --port 8081 -a nuextract3-q8_0 --jinja -c 32768 -np 1

llama-server -hf prithivMLmods/LightOnOCR-3-4B-GGUF:Q8_0 `
  --host 0.0.0.0 --port 8082 -a lightonocr-3-4b --jinja -c 16384 -np 1 --reasoning off
```

## Throughput (`-np`)

Each slot gets its own context window. Match `LLAMACPP_PARALLEL` to the worker concurrency
(`AUDIT_WORKER_CONCURRENCY`, Helm `worker.concurrency`): runs beyond it wait in the queue.

```powershell
pnpm llamacpp:restart
docker compose --profile workers restart worker
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Slow first request | The first image also loads the vision projector |
| `/v1/models` has no multimodal capability | Check the `*_MMPROJ` path |
| Model alias mismatch | Align `*_MODEL_ALIAS` with `AUDIT_*_SERVED_MODEL` |
| Vulkan `ErrorDeviceLost` on large pages | Update llama.cpp (`winget upgrade ggml.llamacpp`); report it upstream with the page |

Logs: `deploy/llamacpp/logs/` (`<model>-llama-server.*.log`).
