from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RoleCode(StrEnum):
    CUSTOMER = "customer"
    KITCHEN = "kitchen"
    MANAGER = "manager"
    OWNER = "owner"


class PublicationState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class AvailabilityState(StrEnum):
    AVAILABLE = "available"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    SCHEDULED = "scheduled"


class TimestampedUUIDMixin:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Role(TimestampedUUIDMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "code IN ('customer', 'kitchen', 'manager', 'owner')",
            name="code_allowed",
        ),
    )

    code: Mapped[RoleCode] = mapped_column(String(32), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    users: Mapped[list[User]] = relationship(back_populates="role")


class User(TimestampedUUIDMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lower"),)

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[Role] = relationship(back_populates="users")


class Location(TimestampedUUIDMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("slug = lower(slug)", name="location_slug_lower"),
        CheckConstraint("preparation_minutes >= 0", name="preparation_non_negative"),
        CheckConstraint("demo_capacity >= 0", name="capacity_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    address_text: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_instructions: Mapped[str | None] = mapped_column(Text)
    delivery_area_text: Mapped[str | None] = mapped_column(Text)
    pickup_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    delivery_available: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    preparation_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=25
    )
    demo_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hours: Mapped[list[OperatingHour]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )


class OperatingHour(TimestampedUUIDMixin, Base):
    __tablename__ = "operating_hours"
    __table_args__ = (
        UniqueConstraint("location_id", "weekday", name="location_weekday"),
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="weekday_range"),
        CheckConstraint(
            "(is_closed = true AND opens_at IS NULL AND closes_at IS NULL) "
            "OR (is_closed = false AND opens_at IS NOT NULL "
            "AND closes_at IS NOT NULL AND opens_at < closes_at)",
            name="valid_time_range",
        ),
    )

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    opens_at: Mapped[time | None] = mapped_column(Time)
    closes_at: Mapped[time | None] = mapped_column(Time)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    location: Mapped[Location] = relationship(back_populates="hours")


class MediaAsset(TimestampedUUIDMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="byte_size_positive"),
        CheckConstraint("width > 0 AND height > 0", name="dimensions_positive"),
        CheckConstraint(
            "focal_point_x >= 0 AND focal_point_x <= 100 "
            "AND focal_point_y >= 0 AND focal_point_y <= 100",
            name="focal_point_range",
        ),
        CheckConstraint(
            "publication_state IN ('draft', 'published')",
            name="publication_state_allowed",
        ),
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    alt_text: Mapped[str] = mapped_column(String(500), nullable=False)
    focal_point_x: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    focal_point_y: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    source_description: Mapped[str | None] = mapped_column(String(500))
    credit: Mapped[str | None] = mapped_column(String(500))
    publication_state: Mapped[PublicationState] = mapped_column(
        String(16), nullable=False, default=PublicationState.DRAFT
    )


class Category(TimestampedUUIDMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("slug = lower(slug)", name="category_slug_lower"),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    menu_items: Mapped[list[MenuItem]] = relationship(back_populates="category")
    media: Mapped[MediaAsset | None] = relationship()


class MenuItem(TimestampedUUIDMixin, Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        CheckConstraint("slug = lower(slug)", name="menu_item_slug_lower"),
        CheckConstraint("base_price_minor >= 0", name="base_price_non_negative"),
        CheckConstraint(
            "length(currency_code) = 3 AND currency_code = upper(currency_code)",
            name="currency_code_uppercase",
        ),
        CheckConstraint(
            "publication_state IN ('draft', 'published')",
            name="publication_state_allowed",
        ),
    )

    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ingredients: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    dietary_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    base_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    publication_state: Mapped[PublicationState] = mapped_column(
        String(16), nullable=False, default=PublicationState.DRAFT
    )
    category: Mapped[Category] = relationship(back_populates="menu_items")
    media: Mapped[MediaAsset | None] = relationship()
    option_groups: Mapped[list[OptionGroup]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan"
    )


class MenuItemAvailability(TimestampedUUIDMixin, Base):
    __tablename__ = "menu_item_availability"
    __table_args__ = (
        UniqueConstraint("location_id", "menu_item_id", name="location_item"),
        CheckConstraint(
            "state IN ('available', 'temporarily_unavailable', 'scheduled')",
            name="state_allowed",
        ),
        CheckConstraint(
            "available_from IS NULL OR available_until IS NULL "
            "OR available_until > available_from",
            name="valid_schedule_range",
        ),
    )

    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id"), nullable=False
    )
    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    state: Mapped[AvailabilityState] = mapped_column(
        String(32), nullable=False, default=AvailabilityState.AVAILABLE
    )
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CuratedCollection(TimestampedUUIDMixin, Base):
    __tablename__ = "curated_collections"
    __table_args__ = (
        CheckConstraint("slug = lower(slug)", name="collection_slug_lower"),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
        CheckConstraint(
            "publication_state IN ('draft', 'published')",
            name="publication_state_allowed",
        ),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publication_state: Mapped[PublicationState] = mapped_column(
        String(16), nullable=False, default=PublicationState.DRAFT
    )


class CollectionMenuItem(TimestampedUUIDMixin, Base):
    __tablename__ = "collection_menu_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "menu_item_id", name="collection_item"),
    )

    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("curated_collections.id"), nullable=False
    )
    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Allergen(TimestampedUUIDMixin, Base):
    __tablename__ = "allergens"
    __table_args__ = (
        CheckConstraint("slug = lower(slug)", name="allergen_slug_lower"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class MenuItemAllergen(TimestampedUUIDMixin, Base):
    __tablename__ = "menu_item_allergens"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "allergen_id", name="item_allergen"),
    )

    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False
    )
    allergen_id: Mapped[UUID] = mapped_column(
        ForeignKey("allergens.id"), nullable=False, index=True
    )
    note: Mapped[str | None] = mapped_column(String(500))


class OptionGroup(TimestampedUUIDMixin, Base):
    __tablename__ = "option_groups"
    __table_args__ = (
        CheckConstraint("minimum_selections >= 0", name="minimum_non_negative"),
        CheckConstraint(
            "maximum_selections >= minimum_selections", name="maximum_gte_minimum"
        ),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
    )

    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    minimum_selections: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    maximum_selections: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    menu_item: Mapped[MenuItem] = relationship(back_populates="option_groups")
    options: Mapped[list[Option]] = relationship(
        back_populates="option_group", cascade="all, delete-orphan"
    )


class Option(TimestampedUUIDMixin, Base):
    __tablename__ = "options"
    __table_args__ = (
        CheckConstraint("price_delta_minor >= 0", name="price_delta_non_negative"),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
    )

    option_group_id: Mapped[UUID] = mapped_column(
        ForeignKey("option_groups.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    price_delta_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    option_group: Mapped[OptionGroup] = relationship(back_populates="options")


class HomeContent(TimestampedUUIDMixin, Base):
    __tablename__ = "home_content"
    __table_args__ = (
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
        CheckConstraint(
            "publication_state IN ('draft', 'published')",
            name="publication_state_allowed",
        ),
    )

    content_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    heading: Mapped[str] = mapped_column(String(240), nullable=False)
    supporting_copy: Mapped[str] = mapped_column(Text, nullable=False)
    action_label: Mapped[str | None] = mapped_column(String(100))
    action_href: Mapped[str | None] = mapped_column(String(255))
    media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), index=True
    )
    menu_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("menu_items.id"), index=True
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    publication_state: Mapped[PublicationState] = mapped_column(
        String(16), nullable=False, default=PublicationState.DRAFT
    )
    media: Mapped[MediaAsset | None] = relationship()
    menu_item: Mapped[MenuItem | None] = relationship()


def model_metadata() -> Any:
    """Expose metadata for Alembic without importing application routes."""

    return Base.metadata
