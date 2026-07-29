# llama-server + NuExtract3 for Repody

Serve [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) with the official
**llama-server** binary (`winget install llama.cpp`). Platform wiring: `docs/REPODY-VLM.md`.

## 1. Install llama.cpp

```powershell
winget install llama.cpp
# later: winget upgrade ggml.llamacpp   # pulls latest GitHub Vulkan release
```

Confirm your GPU backend:

```powershell
llama-server --list-devices
```

Use the device id in `paths.local.env` (e.g. `Vulkan0`, `CUDA0`).

## 2. Download the model

| File | Purpose |
|------|---------|
| `NuExtract3-Q8_0.gguf` | Text weights (~4.5 GB) — **deep-bench winner on Arc** |
| `NuExtract3-Q6_K.gguf` | Strong runner-up (~3.5 GB) |
| `NuExtract3-Q4_K_M.gguf` | Smaller / faster (~2.7 GB) — official HF “local default” |
| `mmproj-NuExtract3-BF16.gguf` | Vision projector (required for images) |

## 3. Configure paths

```powershell
copy deploy\llamacpp\paths.local.env.example deploy\llamacpp\paths.local.env
```

## 4. Start the server

```powershell
pnpm llamacpp:serve
pnpm llamacpp:verify
```

Command reference: [../../docs/COMMANDS.md](../../docs/COMMANDS.md).

### Server flags (aligned with NuExtract + llama.cpp docs)

The launcher (`deploy/scripts/llamacpp-nuextract3.mjs`) starts llama-server with the official
minimal multimodal command plus accuracy / GPU knobs from upstream docs:

| Setting | Value | Source |
|---------|-------|--------|
| Context | **16384** (`-c`) | NuExtract vLLM `--max-model-len 16384` |
| Model + mmproj | **Q4_K_M** + BF16 mmproj | NuExtract3-GGUF (official local) |
| GPU offload | `-ngl 99` + `--mmproj-offload` + `--device Vulkan0` | llama.cpp multimodal |
| Flash Attention | `-fa on` | llama.cpp (`LLAMACPP_FLASH_ATTN`) |
| Chat template | `--jinja` | Required for `chat_template_kwargs` |
| Server reasoning | `-rea off` | Official non-thinking (`enable_thinking=false`) |
| Parallel slots | **1** (`-np 1`) default | Full 16k context per slot |
| Vision tokens | `--image-min/max-tokens` (default **1024** in `paths.local.env.example` / serve script) | Qwen-VL floor is 1024; Arc: keep max capped. Raise toward 1536 only with GPU headroom |
| Vision batch | `-ub` + `--mtmd-batch-max-tokens` match vision budget | Must track image-max-tokens |

**Recommendation:** `NuExtract3-Q8_0.gguf` + vision **1024**. Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_LLAMACPP_SERVED_MODEL`.

API: `http://127.0.0.1:8081/v1` (model id from `LLAMACPP_MODEL_ALIAS`).

## 5. Point Repody at llama-server

```powershell
# backend/.env already sets AUDIT_LLAMACPP_BASE_URL=http://127.0.0.1:8081/v1 for Compose dev
pnpm dev:restart
```

See `deploy/llamacpp/repody-llamacpp.env.example`.

## Manual command (minimal)

```powershell
llama-server `
  -m C:\path\to\NuExtract3-Q4_K_M.gguf `
  --mmproj C:\path\to\mmproj-NuExtract3-BF16.gguf `
  --host 0.0.0.0 --port 8081 `
  -c 16384 -np 1 -ub 1536 `
  -ngl 99 -fa on --device Vulkan0 --mmproj-offload `
  --image-min-tokens 1536 --image-max-tokens 1536 `
  --mtmd-batch-max-tokens 1536 `
  -a nuextract3-q4_k_m --jinja -rea off
```

## Throughput scaling (`-np` / parallel slots)

Each parallel slot reserves a full context window. Throughput scales roughly linearly with `-np` until VRAM or CPU saturates.

| Slots | When | Worker pool |
|-------|------|-------------|
| **1** | CRC lab, Arc 8 GB, daily dev | `workerExtract.maxJobs: 1` |
| **2** | Arc 16 GB+, dedicated stress runs | 2 extract workers or `maxJobs: 2` |
| **4+** | Multi-GPU / production vLLM | Match extract worker concurrency to GPU slots; excess runs wait in Taskiq |

In `paths.local.env`:

```env
LLAMACPP_PARALLEL=2
```

Then align cluster admission (see `deploy/client/lab/values.stress-test.crc.yaml`) and restart:

```powershell
pnpm llamacpp:restart
pnpm dev:restart
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Slow first request | Run `pnpm llamacpp:warmup` or set `LLAMACPP_WARMUP=on` |
| `failed to process image` / Vulkan `ErrorDeviceLost` | Cap `--image-max-tokens` (and match `-ub` / `--mtmd-batch-max-tokens`). Try 1536 first; if unstable, fall back to 1024. Restart with `pnpm llamacpp:restart`. |
| `/v1/models` missing multimodal | Check `LLAMACPP_MMPROJ` path and `--mmproj-offload` |
| Model alias mismatch | Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_LLAMACPP_SERVED_MODEL` |

Logs: `deploy/llamacpp/logs/`.
