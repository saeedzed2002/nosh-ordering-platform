from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.services.database import check_database

router = APIRouter(prefix="/api/v1", tags=["System"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


class ComponentHealth(BaseModel):
    status: Literal["ok", "unavailable"]


class ReadinessHealth(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    database: ComponentHealth


class LivenessHealth(BaseModel):
    status: Literal["ok"]


class ApiRoot(BaseModel):
    name: str
    version: str


@router.get("/health", summary="Check API and database readiness")
def read_readiness(response: Response, settings: SettingsDep) -> ReadinessHealth:
    database_available = check_database(settings.database_url)

    if not database_available:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessHealth(
            status="degraded",
            environment=settings.environment,
            database=ComponentHealth(status="unavailable"),
        )

    return ReadinessHealth(
        status="ok",
        environment=settings.environment,
        database=ComponentHealth(status="ok"),
    )


@router.get("/healthz", include_in_schema=False)
def read_liveness() -> LivenessHealth:
    return LivenessHealth(status="ok")


@router.get("", summary="Read API metadata")
def read_api_root() -> ApiRoot:
    return ApiRoot(name="Nosh API", version="v1")
