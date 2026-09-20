from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models import MediaAsset, MenuItem, Role, RoleCode
from app.services.seed import seed_database


def test_migration_creates_phase_4_tables(seeded_settings) -> None:
    inspector = inspect(get_engine(seeded_settings.database_url))

    assert {
        "roles",
        "users",
        "locations",
        "operating_hours",
        "categories",
        "menu_items",
        "curated_collections",
        "media_assets",
        "option_groups",
        "options",
        "allergens",
        "home_content",
    }.issubset(inspector.get_table_names())


def test_seed_is_repeatable_and_creates_the_catalog(seeded_settings) -> None:
    with Session(get_engine(seeded_settings.database_url)) as session:
        seed_database(session, seeded_settings)
        assert session.query(MenuItem).count() == 16
        assert session.query(Role).count() == 3
        assert (
            session.scalar(select(Role).where(Role.code == RoleCode.ADMIN)) is not None
        )
        assert session.query(MediaAsset).count() == 25


def test_seed_requires_an_explicit_local_password(seeded_settings) -> None:
    missing_password_settings = seeded_settings.__class__(
        environment=seeded_settings.environment,
        database_url=seeded_settings.database_url,
        cors_origins=seeded_settings.cors_origins,
        media_root=seeded_settings.media_root,
        jwt_secret=seeded_settings.jwt_secret,
        access_token_minutes=seeded_settings.access_token_minutes,
        refresh_token_minutes=seeded_settings.refresh_token_minutes,
        seed_admin_password=None,
    )
    with Session(get_engine(seeded_settings.database_url)) as session:
        try:
            seed_database(session, missing_password_settings)
        except ValueError as error:
            assert "NOSH_SEED_ADMIN_PASSWORD" in str(error)
        else:
            raise AssertionError("The seed must not run without a local password.")
