from dataclasses import dataclass
from os import getenv
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    cors_origins: tuple[str, ...]
    media_root: Path
    jwt_secret: str | None
    access_token_minutes: int
    refresh_token_minutes: int
    seed_admin_password: str | None


def get_settings() -> Settings:
    raw_origins = getenv("NOSH_CORS_ORIGINS", "http://localhost:5173")
    cors_origins = tuple(
        origin.strip() for origin in raw_origins.split(",") if origin.strip()
    )

    return Settings(
        environment=getenv("NOSH_ENVIRONMENT", "development"),
        database_url=getenv(
            "NOSH_DATABASE_URL",
            "postgresql://nosh:nosh_local_password@localhost:5432/nosh",
        ),
        cors_origins=cors_origins,
        media_root=Path(getenv("NOSH_MEDIA_ROOT", ".nosh-media")),
        jwt_secret=getenv("NOSH_JWT_SECRET") or None,
        access_token_minutes=int(getenv("NOSH_ACCESS_TOKEN_MINUTES", "15")),
        refresh_token_minutes=int(getenv("NOSH_REFRESH_TOKEN_MINUTES", "10080")),
        seed_admin_password=getenv("NOSH_SEED_ADMIN_PASSWORD") or None,
    )
