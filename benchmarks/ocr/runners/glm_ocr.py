# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["glmocr[selfhosted]", "pyyaml", "pypdfium2>=5.14", "pillow"]
# ///
"""GLM-OCR with its official SDK and the Ollama deployment of zai-org/GLM-OCR
(examples/ollama-deploy): the SDK's default config.yaml with the guide's `ocr_api` settings
(localhost:11434, /api/generate, glm-ocr:latest, ollama_generate) and PP-DocLayout-V3 layout on CPU.
Equal footing with whole-page models: `label_task_mapping` reads every region as text (by default it
discards headers and footers and skips images). The page is the SDK's Markdown.

    ollama pull glm-ocr:latest        # Ollama serving on http://localhost:11434
    uv run runners/glm_ocr.py
"""

import tempfile
from importlib.resources import files
from pathlib import Path

import yaml
from common import page_image, run
from glmocr import GlmOcr

config = yaml.safe_load(files("glmocr").joinpath("config.yaml").read_text(encoding="utf-8"))
config["pipeline"]["maas"]["enabled"] = False
config["pipeline"]["ocr_api"].update(
    api_host="localhost", api_port=11434, api_path="/api/generate", model="glm-ocr:latest", api_mode="ollama_generate"
)
# Equal footing: OCR every region as text instead of discarding headers, footers, numbers,
# footnotes, side text and references (`abandon`) or leaving images unread (`skip`).
mapping = config["pipeline"]["layout"]["label_task_mapping"]
mapping["text"] = [*mapping["text"], *mapping.pop("abandon", []), *mapping.pop("skip", [])]
mapping["abandon"], mapping["skip"] = [], []
config_path = Path(tempfile.mkdtemp()) / "config.yaml"
config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
parser = GlmOcr(config_path=str(config_path), layout_device="cpu")


def infer(page: Path) -> str:
    """The SDK takes images and PDFs; PDF pages go in rendered at 200 DPI, images as they are."""
    source = page
    if page.suffix == ".pdf":
        source = Path(tempfile.mkdtemp()) / f"{page.stem}.png"
        page_image(page, dpi=200).save(source)
    return parser.parse(str(source)).markdown_result or ""


run("glm-ocr", {"runtime": "glmocr SDK (layout CPU) + Ollama 0.40 glm-ocr:latest", "weights": "zai-org/GLM-OCR"}, infer)
