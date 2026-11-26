# NuExtract3 on Modal (vLLM, scale to zero, free tier)

[`nuextract.py`](nuextract.py) serves the full BF16 checkpoint
[`numind/NuExtract3`](https://huggingface.co/numind/NuExtract3) with **vLLM**, the way its model card
does ("vLLM deployment"), on one GPU that runs only while documents are being processed. Repody reaches
it like any OpenAI-compatible server. Its requests already follow the card's vLLM examples
(`chat_template_kwargs` with `template`, `instructions` and `mode`; `developer` messages for
examples), so the backend needs no change.

| Choice                                                                                                                                                                                                                                    | Why (source)                                                                                                                                                                                                                                                                             |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| vLLM, full BF16 weights                                                                                                                                                                                                                   | The card's serving engine; NuMind benchmarked on it                                                                                                                                                                                                                                      |
| The card's `vllm serve` flags, unchanged: `--trust-remote-code`, `--limit-mm-per-prompt '{"image": 99, "video": 0}'`, `--chat-template-content-format openai`, `--generation-config vllm`, `--max-model-len 131072`, MTP `qwen3_next_mtp` | Model card. They fit one 24 GB GPU: 8.8 GiB of weights and 238,830 KV tokens, so 1.82 requests of the full 131,072 at once (vLLM's log). vLLM 0.33 still accepts `qwen3_next_mtp`, logging that it is now called `mtp`                                                                   |
| Added for Modal only: `--revision`, `--served-model-name numind/NuExtract3`, `--host`/`--port`, `--enable-sleep-mode`, `--mm-processor-kwargs`                                                                                            | A pinned revision; the card's model id (offline, vLLM would name it after its local path); Modal's proxy port; snapshots; small images enlarged to ~1 MP by the model's processor (a cropped ID card was misread at its default)                                                         |
| Web function (`@app.cls` + `@modal.concurrent` + `@modal.web_server`), not a Modal Server                                                                                                                                                 | [High-performance LLM inference](https://modal.com/docs/guide/high-performance-llm-inference): for bursty workloads Servers are "generally not worth it". A web function waits for a cold container instead of [answering 503](https://modal.com/docs/guide/servers#zero-to-one-scaling) |
| CPU + GPU memory snapshot, vLLM sleep mode, warm-up before the snapshot                                                                                                                                                                   | [vLLM snapshot example](https://modal.com/docs/examples/vllm_snapshot), [Memory Snapshots](https://modal.com/docs/guide/memory-snapshots)                                                                                                                                                |
| Weights downloaded once by a CPU function into a Volume, revision pinned                                                                                                                                                                  | [Model weights](https://modal.com/docs/guide/model-weights)                                                                                                                                                                                                                              |
| `gpu=["L4", "A10"]`                                                                                                                                                                                                                       | L4 first (24 GB, $0.80/h), A10 when no L4 is free ($1.10/h); a T4 has no BF16. Pinning L4 alone was tried on 19 November: staging then waited 3–11 minutes for a free L4, longer than the 10-minute run timeout, so the fallback stays even though it costs a second set of snapshots    |
| `startup_timeout=15 * MINUTES`                                                                                                                                                                                                            | A start that builds a snapshot measured 507 s; without its own limit, a container's start counts against the 600 s request `timeout` ([Timeouts](https://modal.com/docs/guide/timeouts))                                                                                                 |
| `requires_proxy_auth=True`                                                                                                                                                                                                                | [Proxy Tokens](https://modal.com/docs/guide/webhook-proxy-auth): any other request gets 401 and starts nothing                                                                                                                                                                           |
| CUDA 12.9 devel image, `vllm==0.33.0`, `transformers==5.20.2`                                                                                                                                                                             | vLLM's wheels are built for CUDA 12.9 ([vLLM GPU install](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)); Modal's vLLM examples use this base                                                                                                                        |

## Measured (12 November 2026, one-page invoice, L4 or A10)

|                                                                                                               | Time                                                                  |
| ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| First start after a deploy (load, compile, profile for 99 images, warm-up, snapshot) and the first extraction | 507 s                                                                 |
| Start from the snapshot and the first extraction                                                              | **15 s** (measured with a 32k context; the restore path is unchanged) |
| One-page extraction while the container is up                                                                 | **1–4 s**                                                             |
| Two-page bank statement to Markdown                                                                           | 38 s                                                                  |

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
- A snapshot only restores on the worker type that made it ("e.g. CPU flags"), so each GPU type
  needs 2–3 of them: up to ~6 with the fallback. A start that lands on a new worker type builds one,
  even long after a deploy (staging, 23 November: 2 built, 3 restores, then the next run built a third).
- A redeploy makes the old snapshots obsolete.

## Staying inside the free $30/month

The Starter plan includes [$30 of compute a month](https://modal.com/pricing): about 37 hours on an L4
($0.80/h) or 27 on an A10 ($1.10/h). CPU and memory cost a little more on top. A burst of runs costs
the 15 s start, the extractions, and ten idle minutes before the container stops
(`scaledown_window=10 * MINUTES`). The ten minutes keep the model warm while someone tests in the
builder (run, adjust, run again), for up to ~$0.13 of idle time after the last request.

| Usage (L4; A10 about 1.4×)                                   | GPU time    | Cost        |
| ------------------------------------------------------------ | ----------- | ----------- |
| One invoice, then idle                                       | ~10 min     | ~$0.14      |
| 100 invoices in one burst                                    | ~12 min     | ~$0.16      |
| The first 2–3 starts per GPU type after a deploy (snapshots) | ~507 s each | ~$0.11 each |

So $30 covers about 200 isolated sessions or bursts. These estimates are GPU time only.

**What actually cost money on 12 November** (`modal billing report --for today --show-resources`):
$0.96 of compute, all of it covered by the credit.

- 63% went to experiments that are gone now.
- 34% went to setting up and testing this app.
- 73% was billed on A10s, because no L4 was free; the fallback is about 40% dearer per second.

The rules that follow from it:

- **Deploy rarely.** Each deploy discards the snapshots, and the next 2–3 starts per GPU type
  rebuild them at ~5–8 minutes each, roughly $0.25–0.70 per deploy. Ordinary starts after that
  restore a snapshot in 13–18 s (measured on staging, 19 November).
- **Pre-warm after every deploy**, so the slow starts don't fall on real runs:
  ```bash
  uv run --no-project --no-build --with-requirements deploy/modal/requirements.txt \
    python deploy/modal/prewarm.py --env main      # production; --env staging for staging
  ```
  It starts the deployed model eight times and stops it in between, printing each start's time:
  minutes while a snapshot is built, seconds once one is restored. Run it again if the last start
  is still slow (it can land on a worker or GPU type without a snapshot). The builder also wakes the model when someone
  opens Test & deploy with a sample (`POST /v1/model/wake`).
- **Or from GitHub:** Actions → **Deploy model** deploys the app to the chosen environment and
  pre-warms it, with a record in GitHub. Staging first, then `main`. Once, create a token in
  Modal ([Settings → API Tokens](https://modal.com/settings/tokens)) and save it as the repository
  secrets `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET`
  ([Modal's guide](https://modal.com/docs/guide/continuous-deployment)).

- In [Usage & Billing](https://modal.com/settings/usage), set the **spend limit** to **$0**. It caps
  what you pay after credits; once the credit is used, Modal
  [stops workloads](https://modal.com/docs/guide/budgets#spend-limits) instead of charging you.
- Don't set the **Workspace budget** to $0. It caps usage _before_ credits, so it blocks everything,
  the free credit included.
- In the code: `min_containers=0` (nothing kept warm) and `max_containers=1` (never two GPUs).
- In the backend: `AUDIT_INFERENCE_PROBE=false`, so the Settings and builder pages never wake the GPU
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
AUDIT_INFERENCE_BASE_URL=https://<workspace>--repody-nuextract-vllm-serve.<region>.modal.run/v1
AUDIT_INFERENCE_API_KEY=wk-….ws-…         # the token id, a dot, the token secret
AUDIT_INFERENCE_MODEL=numind/NuExtract3
AUDIT_INFERENCE_PROBE=false
AUDIT_MAX_PAGES_PER_DOCUMENT=99
AUDIT_INFERENCE_CONTEXT_TOKENS=131072
```

A request takes at most 99 images (the card's `--limit-mm-per-prompt`), so
`AUDIT_MAX_PAGES_PER_DOCUMENT=99` cuts a longer PDF to its first 99 pages instead of failing.

The tighter limit is the context, 131,072 tokens (`--max-model-len`). One token covers 32 × 32
pixels, so the page sizes are:

| Page at 170 DPI | Tokens | Pages that fit, with the 16k answer budget of a schema with lists |
| --------------- | ------ | ----------------------------------------------------------------- |
| A4              | ~2,700 | ~41                                                               |
| Letter          | ~2,600 | ~43                                                               |
| Legal           | ~3,400 | ~33                                                               |
| A3              | ~5,500 | ~20                                                               |

In-context examples come on top. `AUDIT_INFERENCE_CONTEXT_TOKENS=131072` makes the backend refuse a
document that would not fit (422, when the run starts), instead of vLLM refusing it on the GPU.

`modal deploy` prints the app's dashboard link. To get the URL itself:
`python -c "import modal; print(modal.Cls.from_name('repody-nuextract','Vllm')().serve.get_web_url())"`.

A request that waits through a cold start gets a 303 to its result after 150 s. The openai SDK follows
it. A start that builds a snapshot takes up to about 8.5 minutes, longer than the backend's defaults
(`AUDIT_INFERENCE_TIMEOUT_SECONDS=180`, `AUDIT_RUN_TIMEOUT_MINUTES=5`). So after a deploy, wake the GPU
with the check below until it answers. Do it once per GPU type that comes up, or raise both settings,
to `600` and `12`.

## Staging

Staging has its own copy in the Modal environment `staging` (deploy/vps/README.md, "Staging"):
the same app, with its own weights volume, URL (`<workspace>-staging--repody-nuextract-vllm-serve…`)
and proxy token. Add `--env staging` to the commands above. It costs only while staging runs
documents, plus the first slow starts after each deploy.

## Check it

```bash
curl -L -H "Authorization: Bearer $AUDIT_INFERENCE_API_KEY" "$MODAL_URL/v1/models"
```

Logs: `modal app logs repody-nuextract --since 1h`. Look for "Creating GPU memory snapshot" and
"Restoring Function from memory snapshot". Cost per container is in the dashboard, under the
`repody-nuextract` app.

## Troubleshooting

| Symptom                                                   | Cause and fix                                                                                                          |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Nothing starts; a tiny function also waits forever        | The Workspace budget is $0: raise it, and keep the spend limit at $0                                                   |
| "waiting to be scheduled on a GPU_L4 worker"              | No L4 free right now; the fallback list takes an A10                                                                   |
| `Cannot change … between Server and non-Server` on deploy | Modal keeps the kind of a name; use a new class name                                                                   |
| 401                                                       | No Proxy Token, or the wrong one                                                                                       |
| A slow start after every deploy                           | Expected: a deploy invalidates the snapshots (2–3 per GPU type are taken again). Run `prewarm.py`                      |
| "Container terminated due to preemption"                  | Modal took the GPU back; it restarts the request by itself, from the start of the model load if no snapshot exists yet |

## Update

To move to a new vLLM release or model revision, change the pins in `nuextract.py`. Run `download`
again if the revision changed, then `modal deploy`, then `prewarm.py`.
