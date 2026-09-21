from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import OrderStatus
from app.schemas.cart import CartLineRequest


class CheckoutTiming(StrEnum):
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"


class PaymentScenario(StrEnum):
    SUCCEEDS = "succeeds"
    FAILS = "fails"


class FulfillmentMethodRequest(StrEnum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class CheckoutRequest(BaseModel):
    idempotency_key: str = Field(
        min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$"
    )
    location_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    fulfillment_method: FulfillmentMethodRequest
    timing: CheckoutTiming
    scheduled_for: datetime | None = None
    recipient_name: str = Field(min_length=2, max_length=120)
    recipient_email: str = Field(
        min_length=5,
        max_length=320,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    recipient_phone: str = Field(min_length=7, max_length=30, pattern=r"^[0-9+() .-]+$")
    delivery_address: str | None = Field(default=None, max_length=500)
    fulfillment_instructions: str | None = Field(default=None, max_length=500)
    promotion_code: str | None = Field(default=None, max_length=48)
    payment_scenario: PaymentScenario = PaymentScenario.SUCCEEDS
    lines: list[CartLineRequest] = Field(min_length=1, max_length=30)

    @field_validator(
        "recipient_name", "recipient_email", "recipient_phone", mode="before"
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value cannot be blank.")
        return normalized

    @field_validator(
        "delivery_address",
        "fulfillment_instructions",
        "promotion_code",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("promotion_code")
    @classmethod
    def normalize_promotion_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def validate_fulfillment_details(self) -> "CheckoutRequest":
        if self.timing == CheckoutTiming.SCHEDULED and self.scheduled_for is None:
            raise ValueError("Choose a scheduled time before placing this order.")
        if self.timing == CheckoutTiming.IMMEDIATE and self.scheduled_for is not None:
            raise ValueError("Immediate orders cannot include a scheduled time.")
        if (
            self.fulfillment_method == FulfillmentMethodRequest.DELIVERY
            and self.delivery_address is None
        ):
            raise ValueError("A delivery address is required for delivery orders.")
        line_ids = [line.client_line_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Each cart line needs a unique identifier.")
        return self


class OrderReceiptOptionResponse(BaseModel):
    id: UUID
    name: str
    option_group_name: str
    price_delta_minor: int


class OrderReceiptLineResponse(BaseModel):
    menu_item_slug: str
    menu_item_name: str
    quantity: int
    note: str | None
    unit_price_minor: int
    line_total_minor: int
    currency_code: str
    selected_options: list[OrderReceiptOptionResponse]


class OrderStatusEventResponse(BaseModel):
    status: str
    note: str
    created_at: datetime


class OrderIssueReason(StrEnum):
    CUSTOMER_REQUEST = "customer_request"
    FULFILLMENT_DETAILS = "fulfillment_details"
    KITCHEN_UNAVAILABLE = "kitchen_unavailable"
    SCHEDULE_UNAVAILABLE = "schedule_unavailable"


class OrderStatusTransitionRequest(BaseModel):
    status: OrderStatus
    reason: OrderIssueReason | None = None

    @model_validator(mode="after")
    def validate_reason(self) -> "OrderStatusTransitionRequest":
        needs_reason = {
            OrderStatus.DECLINED,
            OrderStatus.CANCELLED,
            OrderStatus.NEEDS_CONTACT,
        }
        if self.status in needs_reason and self.reason is None:
            raise ValueError("Choose a customer-safe reason for this order status.")
        if self.status not in needs_reason and self.reason is not None:
            raise ValueError(
                "A reason is only used for a contact, decline, or cancellation state."
            )
        return self


class OrderReceiptResponse(BaseModel):
    public_reference: str
    status: str
    created_at: datetime
    scheduled_for: datetime | None
    location_name: str
    location_address: str
    contact_phone: str
    fulfillment_method: str
    pickup_instructions: str | None
    delivery_area: str | None
    preparation_minutes: int
    estimated_fulfillment_at: datetime | None
    currency_code: str
    subtotal_minor: int
    promotion_code: str | None
    promotion_discount_minor: int
    total_minor: int
    payment_message: str
    lines: list[OrderReceiptLineResponse]
    status_events: list[OrderStatusEventResponse]
