from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.cart import CartLineRequest, CartQuoteResponse
from app.schemas.catalog import MediaSummary


class CustomerProfileUpdateRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=2, max_length=120)

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "CustomerProfileUpdateRequest":
        if self.email is None and self.display_name is None:
            raise ValueError("Provide a profile value to update.")
        return self


class CustomerAddressCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    recipient_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30, pattern=r"^[0-9+() .-]+$")
    address_text: str = Field(min_length=4, max_length=500)
    is_default: bool = False

    @field_validator("label", "recipient_name", "phone", "address_text", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value cannot be blank.")
        return normalized


class CustomerAddressUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=80)
    recipient_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(
        default=None, min_length=7, max_length=30, pattern=r"^[0-9+() .-]+$"
    )
    address_text: str | None = Field(default=None, min_length=4, max_length=500)
    is_default: bool | None = None

    @field_validator("label", "recipient_name", "phone", "address_text", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value cannot be blank.")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "CustomerAddressUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("Provide an address value to update.")
        return self


class CustomerAddressResponse(BaseModel):
    id: UUID
    label: str
    recipient_name: str
    phone: str
    address_text: str
    is_default: bool


class CustomerFavoriteResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    final_price_minor: int
    currency_code: str
    media: MediaSummary | None
    is_available: bool


class CustomerOrderHistoryLineResponse(BaseModel):
    id: UUID
    menu_item_slug: str
    menu_item_name: str
    quantity: int
    selected_option_names: list[str]


class CustomerOrderHistoryResponse(BaseModel):
    public_reference: str
    created_at: datetime
    status: str
    fulfillment_method: str
    location_name: str
    currency_code: str
    total_minor: int
    lines: list[CustomerOrderHistoryLineResponse]


class CustomerReorderResponse(BaseModel):
    location_slug: str
    lines: list[CartLineRequest]
    quote: CartQuoteResponse
