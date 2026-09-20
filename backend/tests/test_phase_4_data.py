from datetime import time
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db.session import get_engine
from app.models import (
    Location,
    MediaAsset,
    MenuItem,
    MenuItemAvailability,
    OperatingHour,
    Role,
    RoleCode,
    User,
)
from app.services.seed import seed_database, seeded_id


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
        assert session.query(Role).count() == 4
        roles_by_code = {
            role.code: role for role in session.scalars(select(Role)).all()
        }
        assert set(roles_by_code) == set(RoleCode)
        assert roles_by_code[RoleCode.KITCHEN].id == seeded_id("role:kitchen")
        assert session.query(MediaAsset).count() == 25


def test_seed_restores_rows_with_location_scoped_ids(seeded_settings) -> None:
    with Session(get_engine(seeded_settings.database_url)) as session:
        location = session.scalar(
            select(Location).where(Location.slug == "market-quarter")
        )
        menu_item = session.scalar(
            select(MenuItem).where(MenuItem.slug == "harissa-chicken-bowl")
        )
        assert location is not None
        assert menu_item is not None

        seeded_hour_id = seeded_id("hour:market-quarter:1")
        seeded_availability_id = seeded_id(
            "availability:market-quarter:harissa-chicken-bowl"
        )
        seeded_hour = session.get(OperatingHour, seeded_hour_id)
        seeded_availability = session.get(MenuItemAvailability, seeded_availability_id)
        assert seeded_hour is not None
        assert seeded_availability is not None
        session.delete(seeded_hour)
        session.delete(seeded_availability)

        other_location = Location(
            id=uuid4(),
            name="Second test kitchen",
            slug="second-test-kitchen",
            address_text="2 Test Street",
            pickup_available=True,
            delivery_available=False,
            preparation_minutes=20,
            demo_capacity=10,
            is_published=False,
        )
        session.add(other_location)
        session.flush()
        session.add_all(
            [
                OperatingHour(
                    id=uuid4(),
                    location_id=other_location.id,
                    weekday=1,
                    opens_at=time(12, 0),
                    closes_at=time(20, 0),
                    is_closed=False,
                ),
                MenuItemAvailability(
                    id=uuid4(),
                    location_id=other_location.id,
                    menu_item_id=menu_item.id,
                    state="available",
                ),
            ]
        )
        session.commit()

        seed_database(session, seeded_settings)

        restored_hour = session.get(OperatingHour, seeded_hour_id)
        restored_availability = session.get(
            MenuItemAvailability, seeded_availability_id
        )
        assert restored_hour is not None
        assert restored_hour.location_id == location.id
        assert restored_availability is not None
        assert restored_availability.location_id == location.id


def test_database_constraints_reject_invalid_role_and_media_metadata(
    seeded_settings,
) -> None:
    with Session(get_engine(seeded_settings.database_url)) as session:
        session.add(Role(id=uuid4(), code="admin", label="Legacy admin"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        media = session.scalar(select(MediaAsset))
        assert media is not None
        media.focal_point_x = 101
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_role_migration_maps_legacy_phase_4_codes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database_path = tmp_path / "legacy-phase-4.sqlite3"
    monkeypatch.setenv("NOSH_DATABASE_URL", f"sqlite:///{database_path.as_posix()}")
    get_engine.cache_clear()
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))

    try:
        command.upgrade(alembic_config, "20260920_01")
        with Session(get_engine(f"sqlite:///{database_path.as_posix()}")) as session:
            admin_role_id = uuid4()
            staff_role_id = uuid4()
            customer_role_id = uuid4()
            session.add_all(
                [
                    Role(id=admin_role_id, code="admin", label="Admin"),
                    Role(id=staff_role_id, code="staff", label="Staff"),
                    Role(id=customer_role_id, code="customer", label="Customer"),
                    User(
                        id=uuid4(),
                        email="owner@nosh.example",
                        display_name="Nosh owner",
                        password_hash="not-used-in-migration-test",
                        role_id=admin_role_id,
                        is_active=True,
                    ),
                    User(
                        id=uuid4(),
                        email="manager@nosh.example",
                        display_name="Nosh manager",
                        password_hash="not-used-in-migration-test",
                        role_id=staff_role_id,
                        is_active=True,
                    ),
                    User(
                        id=uuid4(),
                        email="kitchen@nosh.example",
                        display_name="Nosh kitchen",
                        password_hash="not-used-in-migration-test",
                        role_id=staff_role_id,
                        is_active=True,
                    ),
                    User(
                        id=uuid4(),
                        email="maya@example.test",
                        display_name="Maya Reed",
                        password_hash="not-used-in-migration-test",
                        role_id=customer_role_id,
                        is_active=True,
                    ),
                ]
            )
            session.commit()

        command.upgrade(alembic_config, "head")
        with Session(get_engine(f"sqlite:///{database_path.as_posix()}")) as session:
            roles_by_code = {
                role.code: role for role in session.scalars(select(Role)).all()
            }
            assert set(roles_by_code) == {
                RoleCode.OWNER,
                RoleCode.MANAGER,
                RoleCode.CUSTOMER,
                RoleCode.KITCHEN,
            }
            kitchen_user = session.scalar(
                select(User).where(User.email == "kitchen@nosh.example")
            )
            assert kitchen_user is not None
            assert kitchen_user.role_id == roles_by_code[RoleCode.KITCHEN].id
            assert (
                session.scalar(select(User).where(User.email == "maya@nosh.example"))
                is not None
            )
    finally:
        get_engine.cache_clear()


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
