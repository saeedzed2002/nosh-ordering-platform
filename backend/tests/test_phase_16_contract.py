import json
from os import getenv
from pathlib import Path

from app.main import app

CONTRACT_SNAPSHOT = Path(
    getenv(
        "NOSH_CONTRACT_SNAPSHOT",
        Path(__file__).resolve().parents[2] / "docs" / "contracts" / "openapi-v1.json",
    )
)


def test_openapi_v1_snapshot_matches_the_public_application_contract() -> None:
    snapshot = json.loads(CONTRACT_SNAPSHOT.read_text(encoding="utf-8"))
    generated = app.openapi()

    assert generated == snapshot
    assert generated["openapi"].startswith("3.")
    assert generated["info"]["title"] == "Nosh API"
    assert generated["paths"]
    assert all(
        path == "/api/v1" or path.startswith("/api/v1/") for path in generated["paths"]
    )
