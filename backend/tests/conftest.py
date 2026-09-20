from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings, get_settings
from app.db.session import get_engine
from app.services.seed import seed_database


@pytest.fixture
def seeded_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    database_path = tmp_path / "nosh-phase-4.sqlite3"
    media_root = tmp_path / "media"
    monkeypatch.setenv("NOSH_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    monkeypatch.setenv("NOSH_MEDIA_ROOT", str(media_root))
    monkeypatch.setenv("NOSH_JWT_SECRET", "test-only-jwt-secret-at-least-32-bytes")
    monkeypatch.setenv("NOSH_SEED_ADMIN_PASSWORD", "test-admin-password")
    get_engine.cache_clear()
    settings = get_settings()
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    with Session(get_engine(settings.database_url)) as session:
        seed_database(session, settings)
    yield settings
    get_engine.cache_clear()


@pytest.fixture
def seeded_client(seeded_settings: Settings):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client
