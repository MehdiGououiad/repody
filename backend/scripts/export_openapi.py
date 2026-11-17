"""Write what the frontend generates from the API: its OpenAPI schema (``pnpm
codegen:api:types``), and the field-type catalog, which never changes while the API runs, so the
app and the site import it instead of asking for it. CI fails when either is out of date.

Run with ``uv run python scripts/export_openapi.py`` (uv installs the project).
"""

import json
from pathlib import Path

from repody.main import create_app
from repody.schemas.catalog import catalog

API_DIR = Path(__file__).resolve().parents[2] / "lib" / "api"


def main() -> None:
    API_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "openapi.json": create_app().openapi(),
        "catalog.json": catalog().model_dump(mode="json", by_alias=True),
    }
    for name, content in outputs.items():
        path = API_DIR / name
        path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
