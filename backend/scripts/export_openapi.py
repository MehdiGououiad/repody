"""Write the API's OpenAPI schema for the frontend's generated types (``pnpm api:types``).

Run with ``uv run python scripts/export_openapi.py`` (uv installs the project).
"""

import json
from pathlib import Path

from repody.main import create_app

OUTPUT = Path(__file__).resolve().parents[2] / "lib" / "api" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
