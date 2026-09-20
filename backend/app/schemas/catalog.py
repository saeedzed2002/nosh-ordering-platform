from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models import AvailabilityState


class MediaSummary(BaseModel):
    id: UUID
    alt_text: str
    width: int
    height: int


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    display_order: int
    media: MediaSummary | None


class OperatingHourResponse(BaseModel):
    weekday: int
    opens_at: time | None
    closes_at: time | None
    is_closed: bool


class LocationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    address_text: str
    pickup_instructions: str | None
    delivery_area_text: str | None
    pickup_available: bool
    delivery_available: bool
    preparation_minutes: int
    hours: list[OperatingHourResponse]


class AllergenResponse(BaseModel):
    name: str
    slug: str
    note: str | None


class OptionResponse(BaseModel):
    id: UUID
    name: str
    price_delta_minor: int
    display_order: int


class OptionGroupResponse(BaseModel):
    id: UUID
    name: str
    minimum_selections: int
    maximum_selections: int
    display_order: int
    options: list[OptionResponse]


class MenuItemResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    ingredients: list[str]
    dietary_tags: list[str]
    base_price_minor: int
    currency_code: str
    category: CategoryResponse
    availability: AvailabilityState
    media: MediaSummary | None
    allergens: list[AllergenResponse]
    option_groups: list[OptionGroupResponse]


class CuratedCollectionResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    display_order: int


class HomeContentResponse(BaseModel):
    content_key: str
    heading: str
    supporting_copy: str
    action_label: str | None
    action_href: str | None
    display_order: int
    media: MediaSummary | None
