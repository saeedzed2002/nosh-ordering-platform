from fastapi.testclient import TestClient

from app.main import app
from app.routers import health

client = TestClient(app)


def test_liveness_is_available_without_database() -> None:
    response = client.get("/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_success(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda _: True)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == {"status": "ok"}


def test_readiness_reports_database_unavailability(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", lambda _: False)

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == {"status": "unavailable"}
