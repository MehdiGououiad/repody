# NuExtract3 on Modal (vLLM, scale to zero, free tier)

[`nuextract.py`](nuextract.py) serves the full BF16 checkpoint
[`numind/NuExtract3`](https://huggingface.co/numind/NuExtract3) with **vLLM**, the way its model card
does ("vLLM deployment"), on one GPU that runs only while documents are being processed. Repody reaches
it like any OpenAI-compatible server. Its requests already follow the card's vLLM examples
(`chat_template_kwargs` with `template`, `instructions` and `mode`; `developer` messages for
examples), so the backend needs no change.

| Choice | Why (source) |
|---|---|
| vLLM, full BF16 weights | The card's serving engine; NuMind benchmarked on it |
| The card's `vllm serve` flags, unchanged: `--trust-remote-code`, `--limit-mm-per-prompt '{"image": 99, "video": 0}'`, `--chat-template-content-format openai`, `--generation-config vllm`, `--max-model-len 131072`, MTP `qwen3_next_mtp` | Model card. They fit one 24 GB GPU: 8.8 GiB of weights and 238,830 KV tokens, so 1.82 requests of the full 131,072 at once (vLLM's log). vLLM 0.33 still accepts `qwen3_next_mtp`, logging that it is now called `mtp` |
| Added for Modal only: `--revision`, `--served-model-name numind/NuExtract3`, `--host`/`--port`, `--enable-sleep-mode` | A pinned revision; the card's model id (offline, vLLM would name it after its local path); Modal's proxy port; snapshots |
| Web function (`@app.cls` + `@modal.concurrent` + `@modal.web_server`), not a Modal Server | [High-performance LLM inference](https://modal.com/docs/guide/high-performance-llm-inference): for bursty workloads Servers are "generally not worth it". A web function waits for a cold container instead of [answering 503](https://modal.com/docs/guide/servers#zero-to-one-scaling) |
| CPU + GPU memory snapshot, vLLM sleep mode, warm-up before the snapshot | [vLLM snapshot example](https://modal.com/docs/examples/vllm_snapshot), [Memory Snapshots](https://modal.com/docs/guide/memory-snapshots) |
| Weights downloaded once by a CPU function into a Volume, revision pinned | [Model weights](https://modal.com/docs/guide/model-weights) |
| `gpu=["L4", "A10"]` | [GPU fallbacks](https://modal.com/docs/guide/gpu). Both have 24 GB; a T4 has no BF16 |
| `requires_proxy_auth=True` | [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth): any other request gets 401 and starts nothing |
| CUDA 12.9 devel image, `vllm==0.33.0`, `transformers==5.20.2` | vLLM's wheels are built for CUDA 12.9 ([vLLM GPU install](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)); Modal's vLLM examples use this base |

## Measured (12 November 2026, one-page invoice, L4 or A10)

| | Time |
|---|---|
| First start after a deploy (load, compile, profile for 99 images, warm-up, snapshot) and the first extraction | 507 s |
| Start from the snapshot and the first extraction | **15 s** (measured with a 32k context; the restore path is unchanged) |
| One-page extraction while the container is up | **1–4 s** |
| Two-page bank statement to Markdown | 38 s |

The results were correct for every request type Repody sends:
- the invoice PDF (`FAC-2024-001`, `6000`, `2024-01-15`)
- a PNG invoice with nested line items and an enum
- the same PDF with an in-context example
- a French/Arabic ID card photo
- a two-page statement in Markdown mode (headings, HTML tables)

The weights load in about 10 s. The rest of a start without a snapshot is vLLM's compilation, its
memory profiling and flashinfer's one-off kernel build, which is what the snapshot skips.

Notes from the [Memory Snapshots](https://modal.com/docs/guide/memory-snapshots) guide:
- GPU snapshots are an **alpha** feature.
- Each GPU type needs 2–3 snapshots, so expect a few slow starts after each deploy.
- A redeploy makes the old snapshots obsolete.

## Staying inside the free $30/month

The Starter plan includes [$30 of compute a month](https://modal.com/pricing): about 37 hours on an L4
($0.80/h) or 27 on an A10 ($1.10/h). CPU and memory cost a little more on top. A burst of runs costs
the 15 s start, the extractions, and the idle minute before the container stops
(`scaledown_window=60`, Modal's default).

| Usage (L4; A10 about 1.4×) | GPU time | Cost |
|---|---|---|
| One invoice, then idle | ~76 s | ~$0.02 |
| 100 invoices in one burst | ~175 s | ~$0.04 |
| The first 2–3 starts per GPU type after a deploy (snapshots) | ~507 s each | ~$0.11 each |

So $30 covers about 1,500 isolated invoices, or far more when they come in batches. These estimates
are GPU time only.

**What actually cost money on 12 November** (`modal billing report --for today --show-resources`):
$0.96 of compute, all of it covered by the credit.
- 63% went to experiments that are gone now.
- 34% went to setting up and testing this app.
- 73% was billed on A10s, because no L4 was free; the fallback is about 40% dearer per second.

The rules that follow from it:
- **Deploy rarely.** Each deploy discards the snapshots, and the next 2–3 starts per GPU type (up to
  about 6 with two GPU types) rebuild them at ~8 minutes each, roughly $0.35–0.70 per deploy. Ordinary
  starts after that take 15 s.
- **Wake it once after a deploy** with the check below, so the slow starts don't fall on real runs.
- **Want it cheaper still?** Use `gpu="L4"` alone: half as many snapshots, and no A10 price. A run then
  waits whenever no L4 is free. Waiting is not billed, but the run can time out.

- In [Usage & Billing](https://modal.com/settings/usage), set the **spend limit** to **$0**. It caps
  what you pay after credits; once the credit is used, Modal
  [stops workloads](https://modal.com/docs/guide/budgets#spend-limits) instead of charging you.
- Don't set the **Workspace budget** to $0. It caps usage *before* credits, so it blocks everything,
  the free credit included.
- In the code: `min_containers=0` (nothing kept warm) and `max_containers=1` (never two GPUs).
- In the backend: `AUDIT_LLAMACPP_PROBE=false`, so the Settings and builder pages never wake the GPU
  just to show its status.

## Security

- The endpoint is private: Modal's proxy rejects any request without the Proxy Token (401), before it
  reaches a container. The token lives in the backend's runtime Secret.
- Snapshots need vLLM's dev mode (`VLLM_SERVER_DEV_MODE=1`), which adds the `/sleep` and `/wake_up`
  routes. They are behind the same token, so only the backend can reach them.
- The server runs the pinned revision offline (`HF_HUB_OFFLINE=1`). It never fetches code or weights
  from the Hub at start, although `--trust-remote-code` is set as the card asks.

## Set up (once)

```bash
uv tool install modal==1.6.4
```

```bash
modal setup
```

```bash
modal run deploy/modal/nuextract.py::download
```

```bash
modal deploy deploy/modal/nuextract.py
```

Then create a Proxy Token in [Settings → Proxy Auth Tokens](https://modal.com/settings/proxy-auth-tokens),
or with `modal workspace proxy-tokens create`. The secret is shown only once.

## Point Repody at it

Set these in the backend's environment (in production, the runtime Secret; never commit the token):

```bash
AUDIT_LLAMACPP_BASE_URL=https://<workspace>--repody-nuextract-vllm-serve.<region>.modal.run/v1
AUDIT_LLAMACPP_API_KEY=wk-….ws-…         # the token id, a dot, the token secret
AUDIT_LLAMACPP_SERVED_MODEL=numind/NuExtract3
AUDIT_LLAMACPP_PROBE=false
```

Documents of up to 99 pages fit one request (the card's `--limit-mm-per-prompt`).

`modal deploy` prints the app's dashboard link. To get the URL itself:
`python -c "import modal; print(modal.Cls.from_name('repody-nuextract','Vllm')().serve.get_web_url())"`.

A request that waits through a cold start gets a 303 to its result after 150 s. The openai SDK follows
it. A start that builds a snapshot takes up to about 8.5 minutes, longer than the backend's defaults
(`AUDIT_INFERENCE_TIMEOUT_SECONDS=180`, `AUDIT_RUN_TIMEOUT_MINUTES=5`). So after a deploy, wake the GPU
with the check below until it answers. Do it once per GPU type that comes up, or raise both settings,
to `600` and `12`.

## Check it

```bash
curl -L -H "Authorization: Bearer $AUDIT_LLAMACPP_API_KEY" "$MODAL_URL/v1/models"
```

Logs: `modal app logs repody-nuextract --since 1h`. Look for "Creating GPU memory snapshot" and
"Restoring Function from memory snapshot". Cost per container is in the dashboard, under the
`repody-nuextract` app.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Nothing starts; a tiny function also waits forever | The Workspace budget is $0: raise it, and keep the spend limit at $0 |
| "waiting to be scheduled on a GPU_L4 worker" | No L4 free right now; the fallback list takes an A10 |
| `Cannot change … between Server and non-Server` on deploy | Modal keeps the kind of a name; use a new class name |
| 401 | No Proxy Token, or the wrong one |
| A slow start after every deploy | Expected: a deploy invalidates the snapshots (2–3 per GPU type are taken again) |

## Update

To move to a new vLLM release or model revision, change the pins in `nuextract.py`. Run `download`
again if the revision changed, then `modal deploy`.
