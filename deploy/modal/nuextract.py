"""NuExtract3 on vLLM, as a Modal web function on one GPU that scales to zero.

The model card's serving (https://huggingface.co/numind/NuExtract3, "vLLM deployment") in the
layout Modal recommends for bursty inference (https://modal.com/docs/guide/
high-performance-llm-inference): a web function with input concurrency, started from a CPU + GPU
memory snapshot (https://modal.com/docs/examples/vllm_snapshot, /docs/guide/memory-snapshots).
Also: model weights (/docs/guide/model-weights), GPU fallbacks (/docs/guide/gpu), Proxy Tokens
(/docs/guide/webhook-proxy-auth). Setup, budget and measurements: deploy/modal/README.md.

    modal run deploy/modal/nuextract.py::download   # once: the checkpoint into a Volume (CPU)
    modal deploy deploy/modal/nuextract.py          # prints the URL
    python deploy/modal/prewarm.py                  # after each deploy (see prewarm.py)
"""

import base64
import io
import json
import socket
import subprocess
import time
import urllib.request

import modal

MINUTES = 60  # seconds

# The full BF16 checkpoint, pinned (Modal: "include a revision to prevent surprises").
MODEL = "numind/NuExtract3"
MODEL_REVISION = "c99dc8f5641b866aa0192b6ea78f84bf9f3535f1"
HF_CACHE = "/root/.cache/huggingface"
VLLM_CACHE = "/root/.cache/vllm"
PORT = 8000

# The model card's `vllm serve` command ("vLLM deployment"), flag for flag. It fits one 24 GB
# GPU: the BF16 weights take 8.8 GiB and vLLM measured room for ~235k KV tokens.
CARD_FLAGS = [
    "--trust-remote-code",
    *["--limit-mm-per-prompt", '{"image": 99, "video": 0}'],
    *["--chat-template-content-format", "openai"],
    *["--generation-config", "vllm"],
    *["--max-model-len", "131072"],
    *["--speculative-config", '{"method": "qwen3_next_mtp", "num_speculative_tokens": 2}'],
]
# Pixel bounds for the image processor (see --mm-processor-kwargs below).
IMAGE_SIZE = {"shortest_edge": 1024 * 1024, "longest_edge": 16_777_216}
MAX_INPUTS = 4  # requests Modal sends one container at once (@modal.concurrent)

# vLLM's wheels are built for CUDA 12.9 (docs.vllm.ai, GPU installation); the CUDA devel base with
# add_python is Modal's vLLM example image. transformers: the newest vLLM 0.33.0 accepts.
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.0-devel-ubuntu22.04"
        "@sha256:26cd7d00c09c1f3ff187929c7f4aa7e9273020cb18e86730f40e062e8ffa4d33",
        add_python="3.12",
    )
    .entrypoint([])
    .uv_pip_install("vllm==0.33.0", "transformers==5.20.2", "huggingface-hub==2.4.0")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",  # faster model transfers
            "HF_HUB_OFFLINE": "1",  # serve the pinned revision from the Volume, never the Hub
            # Snapshots (Modal's vLLM snapshot example): sleep mode is a vLLM dev-mode endpoint,
            # and one inductor thread keeps torch.compile snapshot-safe.
            "VLLM_SERVER_DEV_MODE": "1",
            "TORCHINDUCTOR_COMPILE_THREADS": "1",
        }
    )
)

hf_cache = modal.Volume.from_name("repody-nuextract-hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("repody-nuextract-vllm-cache", create_if_missing=True)

app = modal.App("repody-nuextract")


@app.function(
    image=image.env({"HF_HUB_OFFLINE": "0"}), volumes={HF_CACHE: hf_cache}, timeout=30 * MINUTES
)
def download() -> None:
    """The pinned checkpoint (weights, MTP head, processor, chat template) into the Volume, on a
    CPU so no GPU time is spent on it."""
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=MODEL, revision=MODEL_REVISION)
    hf_cache.commit()
    print(f"{MODEL}@{MODEL_REVISION[:7]} is in the Volume: {path}")


@app.cls(
    image=image,
    # Tried in order: L4 (24 GB, $0.80/h), else A10 (24 GB, $1.10/h). A T4 has no BF16. Not L4
    # alone: on 19 November staging waited 3-11 minutes for a free L4, past the 10-minute run
    # timeout. The fallback costs a second set of snapshots after each deploy (README).
    gpu=["L4", "A10"],
    volumes={HF_CACHE: hf_cache, VLLM_CACHE: vllm_cache},
    # Scale to zero, and one container at most: a second GPU would double the cost.
    min_containers=0,
    max_containers=1,
    # Idle time before the container stops: ten minutes, so a person testing in the builder (run,
    # adjust, run again) keeps a warm model. Up to ~$0.13 of idle L4 time after the last request.
    scaledown_window=10 * MINUTES,
    timeout=10 * MINUTES,  # per request
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},  # alpha
)
@modal.concurrent(max_inputs=MAX_INPUTS)
class Vllm:
    @modal.enter(snap=True)
    def start(self) -> None:
        """Start vLLM, warm it up and put it to sleep: the state the snapshot keeps."""
        cmd = [
            "vllm",
            "serve",
            MODEL,
            *CARD_FLAGS,
            # Added for Modal only. The pinned revision, served under the card's model id (offline,
            # vLLM would otherwise name it after its local path), on the port Modal's proxy uses.
            *["--revision", MODEL_REVISION, "--served-model-name", MODEL],
            *["--host", "0.0.0.0", "--port", str(PORT)],  # noqa: S104 - Modal's proxy connects here
            # The model's image processor (Qwen2VLImageProcessor, processor_config.json) keeps any
            # image of at least 65,536 pixels as it is, so a cropped ID card (515x321) reaches the
            # model as ~240 vision tokens and its name lines are misread (5 runs of 5). vLLM's
            # documented --mm-processor-kwargs raises that minimum to ~1 MP: the processor itself
            # enlarges small images (the same card: 5 of 5 right); PDF pages at the card's 170 DPI
            # (~2.8 MP) and photos are larger and stay untouched. longest_edge is the card default.
            *["--mm-processor-kwargs", json.dumps({"size": IMAGE_SIZE})],
            # Weights to CPU memory and the KV cache dropped before the snapshot; Torch
            # compilation and CUDA graphs stay on, since the snapshot keeps their result.
            "--enable-sleep-mode",
        ]
        print(*cmd)
        self.proc = subprocess.Popen(cmd, start_new_session=True)
        wait_ready(self.proc)
        warmup()
        post("/sleep?level=1")

    @modal.enter(snap=False)
    def wake_up(self) -> None:
        post("/wake_up")
        wait_ready(self.proc)

    # Only requests carrying a Proxy Token reach it; others get 401 and start nothing.
    @modal.web_server(port=PORT, startup_timeout=15 * MINUTES, requires_proxy_auth=True)
    def serve(self) -> None:
        pass

    @modal.method()
    def ping(self) -> str:
        """Answers once the model is up: what prewarm.py starts containers with."""
        return "ready"

    @modal.exit()
    def stop(self) -> None:
        self.proc.terminate()


def post(path: str, body: dict | None = None) -> None:
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5 * MINUTES) as response:
        response.read()


def wait_ready(proc: subprocess.Popen) -> None:
    """Block until vLLM answers /health (it does once the model is loaded)."""
    while True:
        if (code := proc.poll()) is not None:
            raise RuntimeError(f"vllm serve exited with code {code}")
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=1).close()
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5):
                return
        except OSError:
            time.sleep(1)


def warmup() -> None:
    """Extraction requests shaped like Repody's (a 170 DPI A4 page, a template), so the vision
    encoder, kernels and CUDA graphs are ready before the snapshot (Modal: warm up first)."""
    from PIL import Image, ImageDraw

    page = Image.new("RGB", (1405, 1987), "white")
    ImageDraw.Draw(page).text((120, 120), "INVOICE FAC-0001  Total 100.00 EUR", fill="black")
    png = io.BytesIO()
    page.save(png, format="PNG")
    url = "data:image/png;base64," + base64.b64encode(png.getvalue()).decode()
    body = {
        "model": MODEL,
        "temperature": 0.2,
        "max_tokens": 64,
        "messages": [
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}}]}
        ],
        "chat_template_kwargs": {
            "template": json.dumps({"invoice_number": "verbatim-string", "total": "number"}),
            "enable_thinking": False,
        },
    }
    for _ in range(3):
        post("/v1/chat/completions", body)
