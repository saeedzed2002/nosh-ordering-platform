from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import FulfillmentMethod, OnlineOrderingState, OrderStatus


class OrderDeskQueue(StrEnum):
    NEEDS_APPROVAL = "needs_approval"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    READY = "ready"
    COMPLETED = "completed"
    ARCHIVE = "archive"


class AdminOrderQueueCount(BaseModel):
    queue: OrderDeskQueue
    label: str
    count: int


class AdminOrderLocationReference(BaseModel):
    id: UUID
    name: str


class AdminOrderListItemResponse(BaseModel):
    public_reference: str
    status: OrderStatus
    fulfillment_method: FulfillmentMethod
    created_at: datetime
    scheduled_for: datetime | None
    location_name: str
    recipient_name: str
    total_minor: int
    currency_code: str
    item_count: int
    queue: OrderDeskQueue


class AdminOrderListResponse(BaseModel):
    orders: list[AdminOrderListItemResponse]
    queue_counts: list[AdminOrderQueueCount]
    locations: list[AdminOrderLocationReference]
    total: int


class AdminOrderAllergenResponse(BaseModel):
    name: str
    slug: str


class AdminOrderLineResponse(BaseModel):
    menu_item_name: str
    quantity: int
    note: str | None
    selected_options: list[str]
    ingredients: list[str]
    dietary_tags: list[str]
    allergens: list[AdminOrderAllergenResponse]


class AdminOrderStatusEventResponse(BaseModel):
    status: OrderStatus
    note: str
    created_at: datetime
    actor_name: str | None


class AdminOrderDetailResponse(AdminOrderListItemResponse):
    recipient_email: str
    recipient_phone: str
    delivery_address: str | None
    fulfillment_instructions: str | None
    pickup_instructions: str | None
    delivery_area: str | None
    lines: list[AdminOrderLineResponse]
    status_events: list[AdminOrderStatusEventResponse]
    valid_next_statuses: list[OrderStatus]


class LocationOrderControlsRequest(BaseModel):
    online_ordering_state: OnlineOrderingState
    online_ordering_paused_until: datetime | None = None
    preparation_minutes: int = Field(ge=0, le=240)
    demo_capacity: int = Field(ge=0, le=10_000)

    @model_validator(mode="after")
    def validate_pause_window(self) -> LocationOrderControlsRequest:
        if self.online_ordering_state == OnlineOrderingState.TIMED_PAUSE:
            if self.online_ordering_paused_until is None:
                raise ValueError("Choose when the timed ordering pause should end.")
            pause_until = self.online_ordering_paused_until
            if pause_until.tzinfo is None:
                raise ValueError(
                    "The timed ordering pause needs a timezone-aware end time."
                )
            if pause_until.astimezone(UTC) <= datetime.now(UTC):
                raise ValueError("The timed ordering pause must end in the future.")
        elif self.online_ordering_paused_until is not None:
            raise ValueError("Only a timed ordering pause can include an end time.")
        return self


class LocationOrderControlsResponse(BaseModel):
    id: UUID
    name: str
    online_ordering_state: OnlineOrderingState
    online_ordering_paused_until: datetime | None
    ordering_available: bool
    ordering_message: str
    preparation_minutes: int
    demo_capacity: int
