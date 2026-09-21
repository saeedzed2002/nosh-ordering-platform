from __future__ import annotations

from datetime import UTC, datetime, time
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


class HomeContentRevisionAction(StrEnum):
    DRAFT_SAVED = "draft_saved"
    PUBLISHED = "published"


class AvailabilityState(StrEnum):
    AVAILABLE = "available"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    SCHEDULED = "scheduled"


class OptionGroupKind(StrEnum):
    CHOICE = "choice"
    EXTRA = "extra"
    REMOVAL = "removal"


class CatalogChangeAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    AVAILABILITY_CHANGED = "availability_changed"
    FEATURED_PLACEMENT_CHANGED = "featured_placement_changed"
    VISIBILITY_CHANGED = "visibility_changed"


class PromotionKind(StrEnum):
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"


class FulfillmentMethod(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class OrderStatus(StrEnum):
    SCHEDULED = "scheduled"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    READY_FOR_COURIER = "ready_for_courier"
    HANDED_TO_CUSTOMER = "handed_to_customer"
    HANDED_TO_COURIER = "handed_to_courier"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    NEEDS_CONTACT = "needs_contact"


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
        CheckConstraint("demo_discount_minor >= 0", name="discount_non_negative"),
        CheckConstraint(
            "demo_discount_minor <= base_price_minor",
            name="discount_lte_base_price",
        ),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
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
    demo_discount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
        CheckConstraint("kind IN ('choice', 'extra', 'removal')", name="kind_allowed"),
    )

    menu_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("menu_items.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[OptionGroupKind] = mapped_column(
        String(16), nullable=False, default=OptionGroupKind.CHOICE
    )
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
    revisions: Mapped[list[HomeContentRevision]] = relationship(
        back_populates="home_content", cascade="all, delete-orphan"
    )


class HomeContentRevision(TimestampedUUIDMixin, Base):
    __tablename__ = "home_content_revisions"
    __table_args__ = (
        CheckConstraint(
            "action IN ('draft_saved', 'published')",
            name="action_allowed",
        ),
    )

    home_content_id: Mapped[UUID] = mapped_column(
        ForeignKey("home_content.id"), nullable=False, index=True
    )
    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media_assets.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    action: Mapped[HomeContentRevisionAction] = mapped_column(
        String(32), nullable=False
    )
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    home_content: Mapped[HomeContent] = relationship(back_populates="revisions")
    actor: Mapped[User] = relationship()
    media: Mapped[MediaAsset | None] = relationship()


class CatalogChange(TimestampedUUIDMixin, Base):
    __tablename__ = "catalog_changes"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('menu_item', 'category', 'collection', 'featured')",
            name="entity_type_allowed",
        ),
        CheckConstraint(
            "action IN ('created', 'updated', 'availability_changed', "
            "'featured_placement_changed', 'visibility_changed')",
            name="action_allowed",
        ),
    )

    actor_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    action: Mapped[CatalogChangeAction] = mapped_column(String(48), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    actor: Mapped[User] = relationship()


class Promotion(TimestampedUUIDMixin, Base):
    __tablename__ = "promotions"
    __table_args__ = (
        CheckConstraint("code = upper(code)", name="code_upper"),
        CheckConstraint("kind IN ('fixed_amount', 'percentage')", name="kind_allowed"),
        CheckConstraint("discount_value > 0", name="discount_value_positive"),
        CheckConstraint("minimum_order_minor >= 0", name="minimum_order_non_negative"),
        CheckConstraint("usage_count >= 0", name="usage_count_non_negative"),
        CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0", name="usage_limit_positive"
        ),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="valid_window",
        ),
        CheckConstraint(
            "(kind = 'fixed_amount' AND discount_value >= 1) "
            "OR (kind = 'percentage' AND discount_value BETWEEN 1 AND 10000)",
            name="discount_value_valid_for_kind",
        ),
    )

    code: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[PromotionKind] = mapped_column(String(24), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_order_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Order(TimestampedUUIDMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "public_reference = upper(public_reference)", name="reference_upper"
        ),
        CheckConstraint(
            "fulfillment_method IN ('pickup', 'delivery')", name="fulfillment_allowed"
        ),
        CheckConstraint(
            "status IN ('scheduled', 'submitted', 'accepted', 'preparing', "
            "'ready_for_pickup', 'ready_for_courier', 'handed_to_customer', "
            "'handed_to_courier', 'out_for_delivery', 'delivered', 'declined', "
            "'cancelled', 'needs_contact')",
            name="status_allowed",
        ),
        CheckConstraint("subtotal_minor >= 0", name="subtotal_non_negative"),
        CheckConstraint(
            "promotion_discount_minor >= 0", name="promotion_discount_non_negative"
        ),
        CheckConstraint(
            "promotion_discount_minor <= subtotal_minor",
            name="promotion_discount_lte_subtotal",
        ),
        CheckConstraint(
            "total_minor = subtotal_minor - promotion_discount_minor",
            name="total_matches_components",
        ),
        CheckConstraint(
            "length(currency_code) = 3 AND currency_code = upper(currency_code)",
            name="currency_code_uppercase",
        ),
    )

    public_reference: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    location_id: Mapped[UUID] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    promotion_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("promotions.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(String(32), nullable=False)
    fulfillment_method: Mapped[FulfillmentMethod] = mapped_column(
        String(16), nullable=False
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recipient_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    fulfillment_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    promotion_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    payment_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    promotion_discount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[Location] = relationship()
    promotion: Mapped[Promotion | None] = relationship()
    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    status_events: Mapped[list[OrderStatusEvent]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(TimestampedUUIDMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_minor >= 0", name="unit_price_non_negative"),
        CheckConstraint("line_total_minor >= 0", name="line_total_non_negative"),
        CheckConstraint(
            "line_total_minor = unit_price_minor * quantity", name="line_total_matches"
        ),
        CheckConstraint(
            "length(currency_code) = 3 AND currency_code = upper(currency_code)",
            name="currency_code_uppercase",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    menu_item_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    menu_item_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    menu_item_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    selected_options_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusEvent(TimestampedUUIDMixin, Base):
    __tablename__ = "order_status_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'submitted', 'accepted', 'preparing', "
            "'ready_for_pickup', 'ready_for_courier', 'handed_to_customer', "
            "'handed_to_courier', 'out_for_delivery', 'delivered', 'declined', "
            "'cancelled', 'needs_contact')",
            name="status_allowed",
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(String(32), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False)
    order: Mapped[Order] = relationship(back_populates="status_events")
    actor: Mapped[User | None] = relationship()


def model_metadata() -> Any:
    """Expose metadata for Alembic without importing application routes."""

    return Base.metadata
