from __future__ import annotations

from datetime import UTC, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import OnlineOrderingState, OrderStatus, PromotionKind, ReviewStatus


class PromotionWriteRequest(BaseModel):
    code: str = Field(min_length=3, max_length=48, pattern=r"^[A-Z0-9-]+$")
    name: str = Field(min_length=2, max_length=160)
    kind: PromotionKind
    discount_value: int = Field(ge=1, le=100_000)
    minimum_order_minor: int = Field(default=0, ge=0, le=1_000_000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1, le=1_000_000)
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Promotion name cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def validate_kind_and_window(self) -> PromotionWriteRequest:
        if self.kind == PromotionKind.PERCENTAGE and self.discount_value > 10_000:
            raise ValueError("Percentage promotions cannot exceed 100 percent.")
        if self.starts_at is not None and self.starts_at.tzinfo is None:
            raise ValueError("Promotion start time must include a timezone.")
        if self.ends_at is not None and self.ends_at.tzinfo is None:
            raise ValueError("Promotion end time must include a timezone.")
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at.astimezone(UTC) <= self.starts_at.astimezone(UTC)
        ):
            raise ValueError("Promotion end time must be after its start time.")
        return self


class PromotionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    kind: PromotionKind
    discount_value: int
    minimum_order_minor: int
    starts_at: datetime | None
    ends_at: datetime | None
    usage_limit: int | None
    usage_count: int
    remaining_uses: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OperatingHourWriteRequest(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: time | None = None
    closes_at: time | None = None
    is_closed: bool

    @model_validator(mode="after")
    def validate_window(self) -> OperatingHourWriteRequest:
        if self.is_closed and (self.opens_at is not None or self.closes_at is not None):
            raise ValueError("Closed days cannot have opening hours.")
        if not self.is_closed and (self.opens_at is None or self.closes_at is None):
            raise ValueError("Open days need both opening and closing times.")
        if (
            not self.is_closed
            and self.opens_at is not None
            and self.closes_at is not None
            and self.opens_at >= self.closes_at
        ):
            raise ValueError("Closing time must be after opening time.")
        return self


class RestaurantSettingsUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address_text: str = Field(min_length=5, max_length=1000)
    contact_phone: str = Field(min_length=7, max_length=30, pattern=r"^[0-9+() .-]+$")
    pickup_instructions: str | None = Field(default=None, max_length=1000)
    delivery_area_text: str | None = Field(default=None, max_length=1000)
    pickup_available: bool
    delivery_available: bool
    preparation_minutes: int = Field(ge=0, le=240)
    demo_capacity: int = Field(ge=0, le=10_000)
    online_ordering_state: OnlineOrderingState
    online_ordering_paused_until: datetime | None = None
    is_published: bool
    hours: list[OperatingHourWriteRequest] = Field(min_length=7, max_length=7)

    @field_validator(
        "name",
        "address_text",
        "contact_phone",
        "pickup_instructions",
        "delivery_area_text",
        mode="before",
    )
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_operations(self) -> RestaurantSettingsUpdateRequest:
        if self.is_published and not (self.pickup_available or self.delivery_available):
            raise ValueError("A published location needs pickup or delivery enabled.")
        if self.online_ordering_state == OnlineOrderingState.TIMED_PAUSE:
            if self.online_ordering_paused_until is None:
                raise ValueError("Choose when the timed ordering pause should end.")
            if self.online_ordering_paused_until.tzinfo is None:
                raise ValueError(
                    "The timed ordering pause needs a timezone-aware end time."
                )
            if self.online_ordering_paused_until.astimezone(UTC) <= datetime.now(UTC):
                raise ValueError("The timed ordering pause must end in the future.")
        elif self.online_ordering_paused_until is not None:
            raise ValueError("Only a timed ordering pause can include an end time.")
        if {hour.weekday for hour in self.hours} != set(range(7)):
            raise ValueError(
                "Provide exactly one operating-hours entry for each weekday."
            )
        return self


class RestaurantSettingsResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    address_text: str
    contact_phone: str
    pickup_instructions: str | None
    delivery_area_text: str | None
    pickup_available: bool
    delivery_available: bool
    preparation_minutes: int
    demo_capacity: int
    online_ordering_state: OnlineOrderingState
    online_ordering_paused_until: datetime | None
    is_published: bool
    hours: list[OperatingHourWriteRequest]


class CustomerAccountStateRequest(BaseModel):
    is_active: bool


class AdminCustomerOrderResponse(BaseModel):
    public_reference: str
    status: OrderStatus
    fulfillment_method: str
    total_minor: int
    currency_code: str
    created_at: datetime


class AdminCustomerResponse(BaseModel):
    id: UUID
    display_name: str
    email: str
    is_active: bool
    created_at: datetime
    order_count: int
    last_order_at: datetime | None
    orders: list[AdminCustomerOrderResponse] = Field(default_factory=list)


class AuditLogResponse(BaseModel):
    id: UUID
    created_at: datetime
    actor_name: str
    entity_type: str
    entity_id: UUID | None
    action: str
    before_snapshot: dict[str, object]
    after_snapshot: dict[str, object]


class ReportStatusDistribution(BaseModel):
    status: OrderStatus
    count: int


class ReportPopularFood(BaseModel):
    menu_item_name: str
    quantity: int
    revenue_minor: int


class ReportPromotionUse(BaseModel):
    code: str
    uses: int
    discount_minor: int


class ReportReviewModeration(BaseModel):
    status: ReviewStatus
    count: int


class AdminReportResponse(BaseModel):
    starts_at: datetime | None
    ends_at: datetime | None
    order_count: int
    revenue_order_count: int
    demo_revenue_minor: int
    average_order_value_minor: int
    popular_food: list[ReportPopularFood]
    status_distribution: list[ReportStatusDistribution]
    promotion_use: list[ReportPromotionUse]
    review_moderation: list[ReportReviewModeration]
