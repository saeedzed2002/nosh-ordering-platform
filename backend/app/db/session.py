from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def sqlalchemy_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache
def get_engine(database_url: str) -> Engine:
    return create_engine(sqlalchemy_database_url(database_url), pool_pre_ping=True)


def get_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Generator[Session]:
    session_factory = sessionmaker(
        bind=get_engine(settings.database_url), expire_on_commit=False
    )
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
