from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str
    cors_origins: tuple[str, ...]


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
    )
