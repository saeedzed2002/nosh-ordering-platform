from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionDep
from app.models import (
    Allergen,
    AvailabilityState,
    Category,
    CuratedCollection,
    HomeContent,
    Location,
    MediaAsset,
    MenuItem,
    MenuItemAllergen,
    MenuItemAvailability,
    OptionGroup,
    OptionGroupKind,
    PublicationState,
)
from app.schemas.catalog import (
    AllergenResponse,
    CategoryResponse,
    CuratedCollectionResponse,
    HomeContentResponse,
    LocationResponse,
    MediaSummary,
    MenuItemResponse,
    OperatingHourResponse,
    OptionGroupResponse,
    OptionResponse,
)

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


def serialize_media(media: MediaAsset | None) -> MediaSummary | None:
    if media is None:
        return None
    return MediaSummary(
        id=media.id, alt_text=media.alt_text, width=media.width, height=media.height
    )


def serialize_category(category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        display_order=category.display_order,
        media=serialize_media(category.media),
    )


def serialize_menu_item(
    item: MenuItem, availability: AvailabilityState, allergens: list[AllergenResponse]
) -> MenuItemResponse:
    return MenuItemResponse(
        id=item.id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        ingredients=item.ingredients,
        dietary_tags=item.dietary_tags,
        base_price_minor=item.base_price_minor,
        demo_discount_minor=item.demo_discount_minor,
        final_price_minor=item.base_price_minor - item.demo_discount_minor,
        currency_code=item.currency_code,
        display_order=item.display_order,
        category=serialize_category(item.category),
        availability=availability,
        media=serialize_media(item.media),
        allergens=allergens,
        option_groups=[
            OptionGroupResponse(
                id=option_group.id,
                name=option_group.name,
                kind=OptionGroupKind(option_group.kind).value,
                minimum_selections=option_group.minimum_selections,
                maximum_selections=option_group.maximum_selections,
                display_order=option_group.display_order,
                options=[
                    OptionResponse(
                        id=option.id,
                        name=option.name,
                        price_delta_minor=option.price_delta_minor,
                        display_order=option.display_order,
                    )
                    for option in sorted(
                        (
                            option
                            for option in option_group.options
                            if option.is_available
                        ),
                        key=lambda option: option.display_order,
                    )
                ],
            )
            for option_group in sorted(
                item.option_groups, key=lambda group: group.display_order
            )
        ],
    )


def effective_availability(
    availability: MenuItemAvailability | None, now: datetime
) -> AvailabilityState:
    if availability is None:
        return AvailabilityState.AVAILABLE
    state = AvailabilityState(availability.state)
    if state != AvailabilityState.SCHEDULED:
        return state
    available_from = availability.available_from
    available_until = availability.available_until
    if available_from is not None and available_from.tzinfo is None:
        available_from = available_from.replace(tzinfo=UTC)
    if available_until is not None and available_until.tzinfo is None:
        available_until = available_until.replace(tzinfo=UTC)
    if (
        available_from is not None
        and available_until is not None
        and available_from <= now < available_until
    ):
        return AvailabilityState.AVAILABLE
    return AvailabilityState.TEMPORARILY_UNAVAILABLE


def resolve_published_location(
    session: SessionDep, location_slug: str | None
) -> Location | None:
    statement = select(Location).where(Location.is_published.is_(True))
    if location_slug is not None:
        location = session.scalar(statement.where(Location.slug == location_slug))
        if location is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="We could not find that location.",
            )
        return location
    return session.scalar(statement.order_by(Location.name).limit(1))


def availability_by_menu_item_id(
    session: SessionDep, items: list[MenuItem], location: Location | None
) -> dict[object, AvailabilityState]:
    if location is None:
        return {item.id: AvailabilityState.AVAILABLE for item in items}
    availability_rows = session.scalars(
        select(MenuItemAvailability).where(
            MenuItemAvailability.location_id == location.id,
            MenuItemAvailability.menu_item_id.in_([item.id for item in items]),
        )
    ).all()
    return {
        availability.menu_item_id: effective_availability(
            availability, datetime.now(UTC)
        )
        for availability in availability_rows
    }


def allergens_by_menu_item_id(
    session: SessionDep, items: list[MenuItem]
) -> dict[object, list[AllergenResponse]]:
    if not items:
        return {}
    allergen_rows = session.execute(
        select(MenuItemAllergen.menu_item_id, Allergen)
        .join(Allergen, Allergen.id == MenuItemAllergen.allergen_id)
        .where(MenuItemAllergen.menu_item_id.in_([item.id for item in items]))
    ).all()
    allergens_by_item_id: dict[object, list[AllergenResponse]] = {}
    for menu_item_id, allergen in allergen_rows:
        allergens_by_item_id.setdefault(menu_item_id, []).append(
            AllergenResponse(name=allergen.name, slug=allergen.slug, note=None)
        )
    return allergens_by_item_id


@router.get("/categories", summary="List published menu categories")
def list_categories(session: SessionDep) -> list[CategoryResponse]:
    categories = session.scalars(
        select(Category)
        .where(Category.is_published.is_(True))
        .options(joinedload(Category.media))
        .order_by(Category.display_order, Category.name)
    ).all()
    return [serialize_category(category) for category in categories]


@router.get("/locations", summary="List published Nosh locations")
def list_locations(session: SessionDep) -> list[LocationResponse]:
    locations = session.scalars(
        select(Location)
        .where(Location.is_published.is_(True))
        .options(selectinload(Location.hours))
        .order_by(Location.name)
    ).all()
    return [
        LocationResponse(
            id=location.id,
            name=location.name,
            slug=location.slug,
            address_text=location.address_text,
            pickup_instructions=location.pickup_instructions,
            delivery_area_text=location.delivery_area_text,
            pickup_available=location.pickup_available,
            delivery_available=location.delivery_available,
            preparation_minutes=location.preparation_minutes,
            hours=[
                OperatingHourResponse(
                    weekday=hour.weekday,
                    opens_at=hour.opens_at,
                    closes_at=hour.closes_at,
                    is_closed=hour.is_closed,
                )
                for hour in sorted(location.hours, key=lambda hour: hour.weekday)
            ],
        )
        for location in locations
    ]


@router.get("/menu-items", summary="List published menu items")
def list_menu_items(
    session: SessionDep,
    category_slug: Annotated[str | None, Query(pattern="^[a-z0-9-]+$")] = None,
    location_slug: Annotated[str | None, Query(pattern="^[a-z0-9-]+$")] = None,
) -> list[MenuItemResponse]:
    statement = (
        select(MenuItem)
        .join(MenuItem.category)
        .where(
            MenuItem.publication_state == PublicationState.PUBLISHED,
            Category.is_published.is_(True),
        )
        .options(
            joinedload(MenuItem.category).joinedload(Category.media),
            joinedload(MenuItem.media),
            selectinload(MenuItem.option_groups).selectinload(OptionGroup.options),
        )
        .order_by(Category.display_order, MenuItem.display_order, MenuItem.name)
    )
    if category_slug is not None:
        statement = statement.where(Category.slug == category_slug)

    items = session.scalars(statement).all()
    location = resolve_published_location(session, location_slug)
    availability_by_item_id = availability_by_menu_item_id(session, items, location)
    allergens_by_item_id = allergens_by_menu_item_id(session, items)

    return [
        serialize_menu_item(
            item,
            availability_by_item_id.get(
                item.id, AvailabilityState.TEMPORARILY_UNAVAILABLE
            ),
            allergens_by_item_id.get(item.id, []),
        )
        for item in items
    ]


@router.get("/menu-items/{slug}", summary="Read a published menu item")
def read_menu_item(
    session: SessionDep,
    slug: Annotated[str, Path(pattern="^[a-z0-9-]+$")],
    location_slug: Annotated[str | None, Query(pattern="^[a-z0-9-]+$")] = None,
) -> MenuItemResponse:
    item = session.scalar(
        select(MenuItem)
        .join(MenuItem.category)
        .where(
            MenuItem.slug == slug,
            MenuItem.publication_state == PublicationState.PUBLISHED,
            Category.is_published.is_(True),
        )
        .options(
            joinedload(MenuItem.category).joinedload(Category.media),
            joinedload(MenuItem.media),
            selectinload(MenuItem.option_groups).selectinload(OptionGroup.options),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that dish.",
        )

    location = resolve_published_location(session, location_slug)
    availability_by_item_id = availability_by_menu_item_id(session, [item], location)
    allergens_by_item_id = allergens_by_menu_item_id(session, [item])
    return serialize_menu_item(
        item,
        availability_by_item_id.get(item.id, AvailabilityState.TEMPORARILY_UNAVAILABLE),
        allergens_by_item_id.get(item.id, []),
    )


@router.get("/collections", summary="List published curated collections")
def list_collections(session: SessionDep) -> list[CuratedCollectionResponse]:
    collections = session.scalars(
        select(CuratedCollection)
        .where(CuratedCollection.publication_state == PublicationState.PUBLISHED)
        .order_by(CuratedCollection.display_order, CuratedCollection.name)
    ).all()
    return [
        CuratedCollectionResponse(
            id=collection.id,
            name=collection.name,
            slug=collection.slug,
            description=collection.description,
            display_order=collection.display_order,
        )
        for collection in collections
    ]


@router.get("/home", summary="Read published home-page content")
def read_home_content(session: SessionDep) -> list[HomeContentResponse]:
    content_blocks = session.scalars(
        select(HomeContent)
        .where(HomeContent.publication_state == PublicationState.PUBLISHED)
        .options(joinedload(HomeContent.media), joinedload(HomeContent.menu_item))
        .order_by(HomeContent.display_order)
    ).all()
    return [
        HomeContentResponse(
            content_key=content.content_key,
            heading=content.heading,
            supporting_copy=content.supporting_copy,
            action_label=content.action_label,
            action_href=content.action_href,
            display_order=content.display_order,
            media=serialize_media(content.media),
            featured_menu_item_slug=(
                content.menu_item.slug if content.menu_item is not None else None
            ),
        )
        for content in content_blocks
    ]
