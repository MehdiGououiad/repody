# llama-server + NuExtract3 for Repody

Serve [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) with the official
**llama-server** binary (`winget install llama.cpp`). Platform wiring: `docs/REPODY-VLM.md`.

## 1. Install llama.cpp

```powershell
winget install llama.cpp
```

Confirm your GPU backend:

```powershell
llama-server --list-devices
```

Use the device id in `paths.local.env` (e.g. `Vulkan0`, `CUDA0`).

## 2. Download the model

| File | Purpose |
|------|---------|
| `NuExtract3-Q4_K_M.gguf` | Text weights (~2.5 GB) — **only supported local model** |
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
| Vision tokens | `--image-min-tokens 1024 --image-max-tokens 1024` | Min = Qwen-VL accuracy floor; max caps vision budget (required on Arc 140V) |
| Vision batch | `-ub 1024` + `--mtmd-batch-max-tokens 1024` | Match the 1024 vision budget |

Solo A/B: `node deploy/llamacpp/bench-stability.mjs` · speed: `node deploy/llamacpp/bench-solo.mjs`

API: `http://127.0.0.1:8081/v1` (model id `nuextract3-q4_k_m` by default; set `LLAMACPP_MODEL_ALIAS`).

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
  -c 16384 -np 1 -ub 1024 `
  -ngl 99 -fa on --device Vulkan0 --mmproj-offload `
  --image-min-tokens 1024 --image-max-tokens 1024 `
  --mtmd-batch-max-tokens 1024 `
  -a nuextract3-q4_k_m --jinja -rea off
```

## Throughput scaling (`-np` / parallel slots)

Each parallel slot reserves a full context window. Throughput scales roughly linearly with `-np` until VRAM or CPU saturates.

| Slots | When | Helm / admission |
|-------|------|------------------|
| **1** | CRC lab, Arc 8 GB, daily dev | `admissionMaxExtractInflight: 1` |
| **2** | Arc 16 GB+, dedicated stress runs | `admissionMaxExtractInflight: 2` + 2 extract workers |
| **4+** | Multi-GPU / production vLLM | Match `admissionMaxExtractInflight` to GPU concurrency |

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
| `failed to process image` / Vulkan `ErrorDeviceLost` | Ensure `--image-max-tokens 1024` and `-ub 1024` / `--mtmd-batch-max-tokens 1024`. Restart with `pnpm llamacpp:restart`. |
| `/v1/models` missing multimodal | Check `LLAMACPP_MMPROJ` path and `--mmproj-offload` |
| Model alias mismatch | Align `LLAMACPP_MODEL_ALIAS` with `AUDIT_LLAMACPP_SERVED_MODEL` |

Logs: `deploy/llamacpp/logs/`.
