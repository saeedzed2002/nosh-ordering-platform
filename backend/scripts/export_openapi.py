"""Write the deterministic public `/api/v1` OpenAPI contract snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
DEFAULT_OUTPUT = PROJECT_ROOT / "docs" / "contracts" / "openapi-v1.json"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the versioned Nosh OpenAPI contract as sorted JSON."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path for the OpenAPI JSON snapshot.",
    )
    return parser.parse_args()


def openapi_document() -> dict[str, object]:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    from app.main import app

    return app.openapi()


def main() -> None:
    arguments = parse_arguments()
    output = arguments.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(openapi_document(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
