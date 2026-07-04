# llama-server + NuExtract3 for Repody

Serve [numind/NuExtract3-GGUF](https://huggingface.co/numind/NuExtract3-GGUF) with the official
**llama-server** binary (`winget install llama.cpp`). This is Repody’s supported local GGUF runtime;
production reference remains vLLM — see `docs/REPODY-VLM.md`.

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
| `NuExtract3-Q4_K_M.gguf` | Text weights (~2.5 GB) — **local Compose default** (Arc Vulkan tuned) |
| `NuExtract3-Q8_0.gguf` | Text weights (~4.5 GB) — higher quality, slower |
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

### Profiles (Vulkan / Intel Arc)

| Profile | When | Key flags | Facture (typical) |
|---------|------|-----------|-------------------|
| **`speed`** (default) | Daily dev | `-fa on`, `-ub 1024`, prompt cache, `GGML_VK_MAX_NODES_PER_SUBMIT=1` | **~7–13 s warm** (Q4, prompt cache) |
| **`stability`** | After `ErrorDeviceLost` | `-fa off`, `-ub 1024`, `-ctv f16`, `--no-cache-prompt`, `GGML_VK_MAX_NODES_PER_SUBMIT=1` | ~2 min |

Set in `paths.local.env`:

```env
LLAMACPP_PROFILE=speed      # default
# LLAMACPP_PROFILE=stability
```

### Load settings (NuExtract + Repody defaults)

Aligned with NuExtract’s low-memory vLLM profile and llama.cpp vision guidance:

| Setting | Value |
|---------|-------|
| Quantization | **Q4_K_M** local default (or **Q8_0**) + BF16 mmproj |
| Context | **16384** |
| Flash attention | **on** in `speed` profile; **off** in `stability` (Intel Vulkan DeviceLost workaround) |
| KV cache | **q8_0** K+V with FA on; **f16** V when FA off |
| Physical batch | **1024** (`speed`, Arc tuned) / **1024** (`stability`) |
| MTMD encode batch | **1024** on Vulkan (`--mtmd-batch-max-tokens`) |
| GPU offload | all layers (`-ngl 99`) + `--mmproj-offload` |
| Parallel slots | **1** (`-np 1`) — full 16k context |
| Image tokens | `--image-min-tokens 1024` (NuExtract / Qwen-VL) |
| Prompt cache | **on** (`speed`) / **off** (`stability`) |
| Server reasoning | off (`-rea off`) — Repody sends `enable_thinking` per request |
| Chat template | `--jinja` (required for `chat_template_kwargs`) |

Tune in `paths.local.env` — see `paths.local.env.example`.

API: `http://127.0.0.1:8081/v1` (model id `nuextract3-q4_k_m` by default; set `LLAMACPP_MODEL_ALIAS`).

## 5. Point Repody at llama-server

```powershell
# backend/.env already sets AUDIT_VLLM_BASE_URL=http://127.0.0.1:8081/v1 for Compose dev
pnpm dev:restart
```

See `deploy/llamacpp/repody-llamacpp.env.example`.

## Manual command (Vulkan / Intel Arc)

```powershell
llama-server `
  -m C:\path\to\NuExtract3-Q4_K_M.gguf `
  --mmproj C:\path\to\mmproj-NuExtract3-BF16.gguf `
  --host 0.0.0.0 --port 8081 `
  -c 16384 -np 1 -fa on -ctk q8_0 -ctv q8_0 `
  -ngl 99 --device Vulkan0 --mmproj-offload `
  --image-min-tokens 1024 --mtmd-batch-max-tokens 1024 -ub 1024 `
  -a nuextract3-q4_k_m --jinja -rea off --cache-ram 2048
```

## Port note

Port **8081** for local dev (`pnpm dev:api` uses `REPODY_API_PORT`, default **8000**).
Production vLLM reference uses 8000.

## Smoke test

```powershell
python deploy/scripts/test-inference-endpoint.py --host http://127.0.0.1:8081
pnpm llamacpp:verify
```
