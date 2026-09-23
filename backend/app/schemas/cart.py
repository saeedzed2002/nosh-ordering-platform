from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.catalog import MediaSummary


class CartLineRequest(BaseModel):
    client_line_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    menu_item_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    quantity: int = Field(ge=1, le=20)
    option_ids: list[UUID] = Field(default_factory=list, max_length=40)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def reject_duplicate_options(self) -> "CartLineRequest":
        if len(self.option_ids) != len(set(self.option_ids)):
            raise ValueError("Each choice may be selected only once.")
        return self


class CartQuoteRequest(BaseModel):
    lines: list[CartLineRequest] = Field(min_length=1, max_length=30)
    location_slug: str | None = Field(default=None, pattern=r"^[a-z0-9-]+$")

    @model_validator(mode="after")
    def reject_duplicate_line_ids(self) -> "CartQuoteRequest":
        line_ids = [line.client_line_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Each cart line needs a unique identifier.")
        return self


class CartSelectedOptionResponse(BaseModel):
    id: UUID
    name: str
    option_group_name: str
    price_delta_minor: int


class CartQuoteLineResponse(BaseModel):
    client_line_id: str
    menu_item_slug: str
    name: str
    media: MediaSummary | None
    quantity: int
    note: str | None
    selected_options: list[CartSelectedOptionResponse]
    unit_price_minor: int
    line_total_minor: int
    currency_code: str


class CartQuoteResponse(BaseModel):
    lines: list[CartQuoteLineResponse]
    subtotal_minor: int
    currency_code: str
