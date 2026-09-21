from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models import AvailabilityState, PublicationState
from app.schemas.catalog import AllergenResponse, CategoryResponse, MediaSummary


class AdminAllergenResponse(AllergenResponse):
    id: UUID
    description: str | None


class AdminMenuMediaResponse(MediaSummary):
    original_filename: str
    publication_state: PublicationState


class AdminLocationReference(BaseModel):
    id: UUID
    name: str
    slug: str


class MenuOptionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price_delta_minor: int = Field(default=0, ge=0)
    is_available: bool = True


class MenuOptionResponse(MenuOptionRequest):
    id: UUID
    display_order: int


class MenuOptionGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="choice", pattern="^(choice|extra|removal)$")
    minimum_selections: int = Field(default=0, ge=0)
    maximum_selections: int = Field(default=1, ge=0)
    options: list[MenuOptionRequest] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_selection_limits(self) -> MenuOptionGroupRequest:
        active_options = sum(option.is_available for option in self.options)
        if self.maximum_selections < self.minimum_selections:
            raise ValueError("The maximum choices must be at least the minimum.")
        if self.maximum_selections > len(self.options):
            raise ValueError("The maximum choices cannot exceed the supplied options.")
        if self.minimum_selections > active_options:
            raise ValueError("Required choices must remain available to customers.")
        if len({option.name.casefold() for option in self.options}) != len(
            self.options
        ):
            raise ValueError("Option names must be unique within a group.")
        return self


class MenuOptionGroupResponse(MenuOptionGroupRequest):
    id: UUID
    display_order: int
    options: list[MenuOptionResponse]


class MenuAvailabilityRequest(BaseModel):
    location_id: UUID
    state: AvailabilityState
    available_from: datetime | None = None
    available_until: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self) -> MenuAvailabilityRequest:
        if self.state == AvailabilityState.SCHEDULED:
            if self.available_from is None or self.available_until is None:
                raise ValueError("A scheduled item needs both a start and an end time.")
            if (
                self.available_from.tzinfo is None
                or self.available_until.tzinfo is None
            ):
                raise ValueError("Scheduled times must include a timezone.")
            if self.available_until <= self.available_from:
                raise ValueError("The schedule end must be after its start.")
        elif self.available_from is not None or self.available_until is not None:
            raise ValueError("Only scheduled availability can include a time window.")
        return self


class MenuAvailabilityResponse(BaseModel):
    id: UUID | None = None
    location_id: UUID
    state: AvailabilityState
    available_from: datetime | None = None
    available_until: datetime | None = None


class MenuItemWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(
        min_length=1, max_length=160, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str = Field(min_length=1, max_length=4000)
    category_id: UUID
    media_id: UUID
    ingredients: list[str] = Field(default_factory=list, max_length=40)
    dietary_tags: list[str] = Field(default_factory=list, max_length=20)
    base_price_minor: int = Field(ge=0)
    demo_discount_minor: int = Field(default=0, ge=0)
    display_order: int = Field(default=0, ge=0)
    publication_state: PublicationState = PublicationState.DRAFT
    allergen_ids: list[UUID] = Field(default_factory=list, max_length=20)
    option_groups: list[MenuOptionGroupRequest] = Field(
        default_factory=list, max_length=12
    )
    availability: MenuAvailabilityRequest

    @model_validator(mode="after")
    def validate_menu_item(self) -> MenuItemWriteRequest:
        if self.demo_discount_minor > self.base_price_minor:
            raise ValueError("The demo discount cannot exceed the base price.")
        if len({ingredient.casefold() for ingredient in self.ingredients}) != len(
            self.ingredients
        ):
            raise ValueError("Ingredients must not repeat.")
        if len({tag.casefold() for tag in self.dietary_tags}) != len(self.dietary_tags):
            raise ValueError("Dietary tags must not repeat.")
        if len({group.name.casefold() for group in self.option_groups}) != len(
            self.option_groups
        ):
            raise ValueError("Option group names must be unique.")
        return self


class CatalogChangeResponse(BaseModel):
    id: UUID
    action: str
    actor_name: str
    created_at: datetime
    snapshot: dict[str, object]


class AdminMenuItemResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    category: CategoryResponse
    media: MediaSummary
    ingredients: list[str]
    dietary_tags: list[str]
    base_price_minor: int
    demo_discount_minor: int
    final_price_minor: int
    currency_code: str
    display_order: int
    publication_state: PublicationState
    allergens: list[AdminAllergenResponse]
    option_groups: list[MenuOptionGroupResponse]
    availability: MenuAvailabilityResponse
    history: list[CatalogChangeResponse] = Field(default_factory=list)


class AdminCategoryResponse(CategoryResponse):
    is_published: bool
    menu_item_count: int


class CategoryWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(
        min_length=1, max_length=120, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str | None = Field(default=None, max_length=2000)
    media_id: UUID | None = None
    display_order: int = Field(default=0, ge=0)
    is_published: bool = True


class CuratedCollectionWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(
        min_length=1, max_length=160, pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str = Field(min_length=1, max_length=4000)
    display_order: int = Field(default=0, ge=0)
    publication_state: PublicationState = PublicationState.DRAFT
    menu_item_ids: list[UUID] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def validate_unique_items(self) -> CuratedCollectionWriteRequest:
        if len(set(self.menu_item_ids)) != len(self.menu_item_ids):
            raise ValueError("A collection can only contain each item once.")
        return self


class CuratedCollectionAdminResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str
    display_order: int
    publication_state: PublicationState
    menu_item_ids: list[UUID]


class FeaturedPlacementRequest(BaseModel):
    menu_item_id: UUID | None = None


class FeaturedPlacementResponse(BaseModel):
    menu_item_id: UUID | None
    menu_item_name: str | None


class AdminMenuSetupResponse(BaseModel):
    categories: list[AdminCategoryResponse]
    allergens: list[AdminAllergenResponse]
    media: list[AdminMenuMediaResponse]
    locations: list[AdminLocationReference]
    collections: list[CuratedCollectionAdminResponse]
    featured: FeaturedPlacementResponse
