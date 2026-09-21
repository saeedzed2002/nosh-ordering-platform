from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionDep
from app.models import (
    Allergen,
    AvailabilityState,
    CatalogChange,
    CatalogChangeAction,
    Category,
    CollectionMenuItem,
    CuratedCollection,
    HomeContent,
    Location,
    MediaAsset,
    MenuItem,
    MenuItemAllergen,
    MenuItemAvailability,
    Option,
    OptionGroup,
    OptionGroupKind,
    PublicationState,
    RoleCode,
    User,
)
from app.routers.catalog import serialize_category, serialize_media
from app.schemas.admin_catalog import (
    AdminAllergenResponse,
    AdminCategoryResponse,
    AdminLocationReference,
    AdminMenuItemResponse,
    AdminMenuMediaResponse,
    AdminMenuSetupResponse,
    CatalogChangeResponse,
    CategoryWriteRequest,
    CuratedCollectionAdminResponse,
    CuratedCollectionWriteRequest,
    FeaturedPlacementRequest,
    FeaturedPlacementResponse,
    MenuAvailabilityRequest,
    MenuAvailabilityResponse,
    MenuItemWriteRequest,
    MenuOptionGroupResponse,
    MenuOptionResponse,
)
from app.services.auth import require_roles

router = APIRouter(prefix="/api/v1/admin/menu", tags=["Admin menu"])
MenuEditorDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def validation_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )


def record_change(
    session: SessionDep,
    actor: User,
    *,
    entity_type: str,
    entity_id: UUID | None,
    action: CatalogChangeAction,
    snapshot: dict[str, object],
) -> None:
    session.add(
        CatalogChange(
            created_at=datetime.now(UTC),
            actor_id=actor.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            snapshot=snapshot,
        )
    )


def menu_item_statement():
    return select(MenuItem).options(
        joinedload(MenuItem.category).joinedload(Category.media),
        joinedload(MenuItem.media),
        selectinload(MenuItem.option_groups).selectinload(OptionGroup.options),
    )


def get_location(session: SessionDep, location_id: UUID) -> Location:
    location = session.get(Location, location_id)
    if location is None:
        raise validation_error("Choose a valid service location.")
    return location


def get_default_location(session: SessionDep) -> Location:
    location = session.scalar(
        select(Location).where(Location.is_published.is_(True)).order_by(Location.name)
    )
    if location is None:
        raise validation_error(
            "Create a published service location before managing a menu."
        )
    return location


def get_menu_item(session: SessionDep, slug: str) -> MenuItem:
    item = session.scalar(menu_item_statement().where(MenuItem.slug == slug))
    if item is None:
        raise not_found("We could not find that menu item.")
    return item


def get_media(session: SessionDep, media_id: UUID) -> MediaAsset:
    media = session.get(MediaAsset, media_id)
    if media is None:
        raise validation_error("Choose an image from the media library.")
    return media


def get_category(session: SessionDep, category_id: UUID) -> Category:
    category = session.scalar(
        select(Category)
        .where(Category.id == category_id)
        .options(joinedload(Category.media))
    )
    if category is None:
        raise validation_error("Choose a valid menu category.")
    return category


def get_allergens(session: SessionDep, allergen_ids: list[UUID]) -> list[Allergen]:
    if not allergen_ids:
        return []
    allergens = session.scalars(
        select(Allergen).where(Allergen.id.in_(allergen_ids))
    ).all()
    if len(allergens) != len(set(allergen_ids)):
        raise validation_error("One or more allergens are no longer available.")
    return allergens


def assert_public_references(
    *, category: Category, media: MediaAsset, state: PublicationState
) -> None:
    if state != PublicationState.PUBLISHED:
        return
    if not category.is_published:
        raise validation_error("Publish the category before publishing this menu item.")
    if PublicationState(media.publication_state) != PublicationState.PUBLISHED:
        raise validation_error(
            "Publish the selected image before publishing this menu item."
        )


def serialize_allergen(allergen: Allergen) -> AdminAllergenResponse:
    return AdminAllergenResponse(
        id=allergen.id,
        name=allergen.name,
        slug=allergen.slug,
        note=None,
        description=allergen.description,
    )


def serialize_collection(
    collection: CuratedCollection, item_ids: list[UUID]
) -> CuratedCollectionAdminResponse:
    return CuratedCollectionAdminResponse(
        id=collection.id,
        name=collection.name,
        slug=collection.slug,
        description=collection.description,
        display_order=collection.display_order,
        publication_state=PublicationState(collection.publication_state),
        menu_item_ids=item_ids,
    )


def menu_item_allergens(
    session: SessionDep, item_ids: list[UUID]
) -> dict[UUID, list[Allergen]]:
    if not item_ids:
        return {}
    grouped: dict[UUID, list[Allergen]] = defaultdict(list)
    rows = session.execute(
        select(MenuItemAllergen.menu_item_id, Allergen)
        .join(Allergen, Allergen.id == MenuItemAllergen.allergen_id)
        .where(MenuItemAllergen.menu_item_id.in_(item_ids))
    ).all()
    for item_id, allergen in rows:
        grouped[item_id].append(allergen)
    return grouped


def menu_item_availability(
    session: SessionDep, item_ids: list[UUID], location_id: UUID
) -> dict[UUID, MenuItemAvailability]:
    if not item_ids:
        return {}
    rows = session.scalars(
        select(MenuItemAvailability).where(
            MenuItemAvailability.location_id == location_id,
            MenuItemAvailability.menu_item_id.in_(item_ids),
        )
    ).all()
    return {availability.menu_item_id: availability for availability in rows}


def menu_item_history(
    session: SessionDep, item_id: UUID
) -> list[CatalogChangeResponse]:
    changes = session.scalars(
        select(CatalogChange)
        .where(
            CatalogChange.entity_type == "menu_item",
            CatalogChange.entity_id == item_id,
        )
        .options(joinedload(CatalogChange.actor))
        .order_by(CatalogChange.created_at.desc(), CatalogChange.id.desc())
        .limit(8)
    ).all()
    return [
        CatalogChangeResponse(
            id=change.id,
            action=CatalogChangeAction(change.action).value,
            actor_name=change.actor.display_name,
            created_at=change.created_at,
            snapshot=change.snapshot,
        )
        for change in changes
    ]


def serialize_menu_item(
    item: MenuItem,
    *,
    availability: MenuItemAvailability | None,
    location_id: UUID,
    allergens: list[Allergen],
    history: list[CatalogChangeResponse] | None = None,
) -> AdminMenuItemResponse:
    if item.media is None:
        raise RuntimeError("Admin menu item has no media after validation.")
    availability_response = MenuAvailabilityResponse(
        id=availability.id if availability is not None else None,
        location_id=availability.location_id
        if availability is not None
        else location_id,
        state=(
            AvailabilityState(availability.state)
            if availability is not None
            else AvailabilityState.AVAILABLE
        ),
        available_from=availability.available_from
        if availability is not None
        else None,
        available_until=availability.available_until
        if availability is not None
        else None,
    )
    return AdminMenuItemResponse(
        id=item.id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        category=serialize_category(item.category),
        media=serialize_media(item.media),
        ingredients=item.ingredients,
        dietary_tags=item.dietary_tags,
        base_price_minor=item.base_price_minor,
        demo_discount_minor=item.demo_discount_minor,
        final_price_minor=item.base_price_minor - item.demo_discount_minor,
        currency_code=item.currency_code,
        display_order=item.display_order,
        publication_state=PublicationState(item.publication_state),
        allergens=[serialize_allergen(allergen) for allergen in allergens],
        option_groups=[
            MenuOptionGroupResponse(
                id=group.id,
                name=group.name,
                kind=OptionGroupKind(group.kind).value,
                minimum_selections=group.minimum_selections,
                maximum_selections=group.maximum_selections,
                display_order=group.display_order,
                options=[
                    MenuOptionResponse(
                        id=option.id,
                        name=option.name,
                        price_delta_minor=option.price_delta_minor,
                        is_available=option.is_available,
                        display_order=option.display_order,
                    )
                    for option in sorted(
                        group.options, key=lambda option: option.display_order
                    )
                ],
            )
            for group in sorted(
                item.option_groups, key=lambda group: group.display_order
            )
        ],
        availability=availability_response,
        history=history or [],
    )


def write_menu_item(
    session: SessionDep,
    item: MenuItem,
    request: MenuItemWriteRequest,
    actor: User,
    *,
    action: CatalogChangeAction,
) -> MenuItem:
    category = get_category(session, request.category_id)
    media = get_media(session, request.media_id)
    assert_public_references(
        category=category,
        media=media,
        state=PublicationState(request.publication_state),
    )
    location = get_location(session, request.availability.location_id)
    allergens = get_allergens(session, request.allergen_ids)

    item.category_id = category.id
    item.media_id = media.id
    item.name = request.name.strip()
    item.slug = request.slug
    item.description = request.description.strip()
    item.ingredients = [
        ingredient.strip() for ingredient in request.ingredients if ingredient.strip()
    ]
    item.dietary_tags = [tag.strip() for tag in request.dietary_tags if tag.strip()]
    item.base_price_minor = request.base_price_minor
    item.demo_discount_minor = request.demo_discount_minor
    item.display_order = request.display_order
    item.publication_state = request.publication_state

    session.execute(
        delete(MenuItemAllergen).where(MenuItemAllergen.menu_item_id == item.id)
    )
    item.option_groups.clear()
    session.flush()
    for allergen in allergens:
        session.add(MenuItemAllergen(menu_item_id=item.id, allergen_id=allergen.id))
    for group_order, group in enumerate(request.option_groups):
        option_group = OptionGroup(
            menu_item_id=item.id,
            name=group.name.strip(),
            kind=group.kind,
            minimum_selections=group.minimum_selections,
            maximum_selections=group.maximum_selections,
            display_order=group_order,
        )
        session.add(option_group)
        session.flush()
        for option_order, option in enumerate(group.options):
            session.add(
                Option(
                    option_group_id=option_group.id,
                    name=option.name.strip(),
                    price_delta_minor=option.price_delta_minor,
                    display_order=option_order,
                    is_available=option.is_available,
                )
            )

    availability = session.scalar(
        select(MenuItemAvailability).where(
            MenuItemAvailability.location_id == location.id,
            MenuItemAvailability.menu_item_id == item.id,
        )
    )
    if availability is None:
        availability = MenuItemAvailability(
            location_id=location.id,
            menu_item_id=item.id,
        )
        session.add(availability)
    availability.state = request.availability.state
    availability.available_from = request.availability.available_from
    availability.available_until = request.availability.available_until

    record_change(
        session,
        actor,
        entity_type="menu_item",
        entity_id=item.id,
        action=action,
        snapshot={
            "name": item.name,
            "slug": item.slug,
            "publication_state": item.publication_state.value,
            "base_price_minor": item.base_price_minor,
            "demo_discount_minor": item.demo_discount_minor,
            "availability": availability.state.value,
        },
    )
    return item


def category_responses(session: SessionDep) -> list[AdminCategoryResponse]:
    counts = dict(
        session.execute(
            select(MenuItem.category_id, func.count(MenuItem.id)).group_by(
                MenuItem.category_id
            )
        ).all()
    )
    categories = session.scalars(
        select(Category)
        .options(joinedload(Category.media))
        .order_by(Category.display_order, Category.name)
    ).all()
    return [
        AdminCategoryResponse(
            **serialize_category(category).model_dump(),
            is_published=category.is_published,
            menu_item_count=counts.get(category.id, 0),
        )
        for category in categories
    ]


def collection_responses(session: SessionDep) -> list[CuratedCollectionAdminResponse]:
    collections = session.scalars(
        select(CuratedCollection).order_by(
            CuratedCollection.display_order, CuratedCollection.name
        )
    ).all()
    mappings = session.scalars(
        select(CollectionMenuItem).order_by(CollectionMenuItem.display_order)
    ).all()
    item_ids_by_collection: dict[UUID, list[UUID]] = defaultdict(list)
    for mapping in mappings:
        item_ids_by_collection[mapping.collection_id].append(mapping.menu_item_id)
    return [
        serialize_collection(collection, item_ids_by_collection[collection.id])
        for collection in collections
    ]


def featured_response(session: SessionDep) -> FeaturedPlacementResponse:
    featured = session.scalar(
        select(HomeContent)
        .where(HomeContent.content_key == "featured-dish")
        .options(joinedload(HomeContent.menu_item))
    )
    return FeaturedPlacementResponse(
        menu_item_id=featured.menu_item_id if featured is not None else None,
        menu_item_name=(
            featured.menu_item.name
            if featured is not None and featured.menu_item is not None
            else None
        ),
    )


@router.get("/setup", summary="Read menu editing references")
def read_setup(session: SessionDep, _: MenuEditorDep) -> AdminMenuSetupResponse:
    media = session.scalars(
        select(MediaAsset).order_by(MediaAsset.created_at.desc())
    ).all()
    allergens = session.scalars(select(Allergen).order_by(Allergen.name)).all()
    locations = session.scalars(
        select(Location).order_by(Location.is_published.desc(), Location.name)
    ).all()
    return AdminMenuSetupResponse(
        categories=category_responses(session),
        allergens=[serialize_allergen(allergen) for allergen in allergens],
        media=[
            AdminMenuMediaResponse(
                **serialize_media(asset).model_dump(),
                original_filename=asset.original_filename,
                publication_state=PublicationState(asset.publication_state),
            )
            for asset in media
        ],
        locations=[
            AdminLocationReference(
                id=location.id, name=location.name, slug=location.slug
            )
            for location in locations
        ],
        collections=collection_responses(session),
        featured=featured_response(session),
    )


@router.get("/categories", summary="List safe-to-hide categories")
def list_categories(
    session: SessionDep, _: MenuEditorDep
) -> list[AdminCategoryResponse]:
    return category_responses(session)


@router.post(
    "/categories", status_code=status.HTTP_201_CREATED, summary="Create a menu category"
)
def create_category(
    request: CategoryWriteRequest, session: SessionDep, actor: MenuEditorDep
) -> AdminCategoryResponse:
    if (
        session.scalar(select(Category.id).where(Category.slug == request.slug))
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That category URL is already in use.",
        )
    if request.media_id is not None:
        media = get_media(session, request.media_id)
        if (
            request.is_published
            and PublicationState(media.publication_state) != PublicationState.PUBLISHED
        ):
            raise validation_error(
                "Publish the category image before making the category live."
            )
    category = Category(
        name=request.name.strip(),
        slug=request.slug,
        description=request.description.strip() if request.description else None,
        media_id=request.media_id,
        display_order=request.display_order,
        is_published=request.is_published,
    )
    session.add(category)
    session.flush()
    record_change(
        session,
        actor,
        entity_type="category",
        entity_id=category.id,
        action=CatalogChangeAction.CREATED,
        snapshot={"name": category.name, "is_published": category.is_published},
    )
    session.commit()
    return next(
        response
        for response in category_responses(session)
        if response.id == category.id
    )


@router.put(
    "/categories/{category_id}", summary="Update or safely hide a menu category"
)
def update_category(
    category_id: UUID,
    request: CategoryWriteRequest,
    session: SessionDep,
    actor: MenuEditorDep,
) -> AdminCategoryResponse:
    category = get_category(session, category_id)
    existing_id = session.scalar(
        select(Category.id).where(Category.slug == request.slug)
    )
    if existing_id is not None and existing_id != category.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That category URL is already in use.",
        )
    if request.media_id is not None:
        media = get_media(session, request.media_id)
        if (
            request.is_published
            and PublicationState(media.publication_state) != PublicationState.PUBLISHED
        ):
            raise validation_error(
                "Publish the category image before making the category live."
            )
    category.name = request.name.strip()
    category.slug = request.slug
    category.description = request.description.strip() if request.description else None
    category.media_id = request.media_id
    category.display_order = request.display_order
    category.is_published = request.is_published
    record_change(
        session,
        actor,
        entity_type="category",
        entity_id=category.id,
        action=CatalogChangeAction.VISIBILITY_CHANGED,
        snapshot={"name": category.name, "is_published": category.is_published},
    )
    session.commit()
    return next(
        response
        for response in category_responses(session)
        if response.id == category.id
    )


@router.get("/collections", summary="List curated menu collections")
def list_collections(
    session: SessionDep, _: MenuEditorDep
) -> list[CuratedCollectionAdminResponse]:
    return collection_responses(session)


def write_collection(
    collection: CuratedCollection,
    request: CuratedCollectionWriteRequest,
    session: SessionDep,
    actor: User,
    action: CatalogChangeAction,
) -> CuratedCollection:
    item_ids = request.menu_item_ids
    if item_ids:
        found_item_ids = set(
            session.scalars(select(MenuItem.id).where(MenuItem.id.in_(item_ids))).all()
        )
        if found_item_ids != set(item_ids):
            raise validation_error(
                "One or more chosen collection items are unavailable."
            )
        if request.publication_state == PublicationState.PUBLISHED:
            published_item_ids = set(
                session.scalars(
                    select(MenuItem.id).where(
                        MenuItem.id.in_(item_ids),
                        MenuItem.publication_state == PublicationState.PUBLISHED,
                    )
                ).all()
            )
            if published_item_ids != set(item_ids):
                raise validation_error(
                    "A public collection can only contain published menu items."
                )
    collection.name = request.name.strip()
    collection.slug = request.slug
    collection.description = request.description.strip()
    collection.display_order = request.display_order
    collection.publication_state = request.publication_state
    session.execute(
        delete(CollectionMenuItem).where(
            CollectionMenuItem.collection_id == collection.id
        )
    )
    for display_order, item_id in enumerate(item_ids):
        session.add(
            CollectionMenuItem(
                collection_id=collection.id,
                menu_item_id=item_id,
                display_order=display_order,
            )
        )
    record_change(
        session,
        actor,
        entity_type="collection",
        entity_id=collection.id,
        action=action,
        snapshot={
            "name": collection.name,
            "publication_state": collection.publication_state.value,
        },
    )
    return collection


@router.post(
    "/collections",
    status_code=status.HTTP_201_CREATED,
    summary="Create a curated collection",
)
def create_collection(
    request: CuratedCollectionWriteRequest, session: SessionDep, actor: MenuEditorDep
) -> CuratedCollectionAdminResponse:
    if (
        session.scalar(
            select(CuratedCollection.id).where(CuratedCollection.slug == request.slug)
        )
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That collection URL is already in use.",
        )
    collection = CuratedCollection(
        id=uuid4(),
        name=request.name.strip(),
        slug=request.slug,
        description=request.description.strip(),
        display_order=request.display_order,
        publication_state=request.publication_state,
    )
    session.add(collection)
    session.flush()
    write_collection(collection, request, session, actor, CatalogChangeAction.CREATED)
    session.commit()
    return next(
        response
        for response in collection_responses(session)
        if response.id == collection.id
    )


@router.put("/collections/{collection_id}", summary="Update a curated collection")
def update_collection(
    collection_id: UUID,
    request: CuratedCollectionWriteRequest,
    session: SessionDep,
    actor: MenuEditorDep,
) -> CuratedCollectionAdminResponse:
    collection = session.get(CuratedCollection, collection_id)
    if collection is None:
        raise not_found("We could not find that collection.")
    existing_id = session.scalar(
        select(CuratedCollection.id).where(CuratedCollection.slug == request.slug)
    )
    if existing_id is not None and existing_id != collection.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That collection URL is already in use.",
        )
    write_collection(collection, request, session, actor, CatalogChangeAction.UPDATED)
    session.commit()
    return next(
        response
        for response in collection_responses(session)
        if response.id == collection.id
    )


@router.get("/featured", summary="Read the home-page featured menu placement")
def read_featured(session: SessionDep, _: MenuEditorDep) -> FeaturedPlacementResponse:
    return featured_response(session)


@router.put("/featured", summary="Place a published menu item on the home page")
def update_featured(
    request: FeaturedPlacementRequest, session: SessionDep, actor: MenuEditorDep
) -> FeaturedPlacementResponse:
    featured = session.scalar(
        select(HomeContent).where(HomeContent.content_key == "featured-dish")
    )
    if featured is None:
        raise not_found("The featured-dish home placement is not configured.")
    item = session.get(MenuItem, request.menu_item_id) if request.menu_item_id else None
    if request.menu_item_id is not None and item is None:
        raise validation_error("Choose a valid menu item for the featured placement.")
    if (
        item is not None
        and PublicationState(item.publication_state) != PublicationState.PUBLISHED
    ):
        raise validation_error("Only a published menu item can be featured publicly.")
    featured.menu_item_id = item.id if item is not None else None
    record_change(
        session,
        actor,
        entity_type="featured",
        entity_id=item.id if item is not None else None,
        action=CatalogChangeAction.FEATURED_PLACEMENT_CHANGED,
        snapshot={"menu_item_name": item.name if item is not None else None},
    )
    session.commit()
    return featured_response(session)


@router.get("", summary="Search and filter menu items")
def list_menu_items(
    session: SessionDep,
    _: MenuEditorDep,
    location_id: UUID | None = None,
    category_id: UUID | None = None,
    publication_state: PublicationState | None = None,
    availability_state: AvailabilityState | None = None,
    query: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
) -> list[AdminMenuItemResponse]:
    location = (
        get_location(session, location_id)
        if location_id
        else get_default_location(session)
    )
    statement = menu_item_statement().join(MenuItem.category)
    if category_id is not None:
        statement = statement.where(MenuItem.category_id == category_id)
    if publication_state is not None:
        statement = statement.where(MenuItem.publication_state == publication_state)
    if query is not None:
        statement = statement.where(
            func.lower(MenuItem.name).contains(query.strip().lower())
        )
    items = (
        session.scalars(
            statement.order_by(
                Category.display_order, MenuItem.display_order, MenuItem.name
            )
        )
        .unique()
        .all()
    )
    allergen_map = menu_item_allergens(session, [item.id for item in items])
    availability_map = menu_item_availability(
        session, [item.id for item in items], location.id
    )
    responses = [
        serialize_menu_item(
            item,
            availability=availability_map.get(item.id),
            location_id=location.id,
            allergens=allergen_map.get(item.id, []),
        )
        for item in items
    ]
    if availability_state is not None:
        responses = [
            response
            for response in responses
            if response.availability.state == availability_state
        ]
    return responses


@router.get("/{slug}", summary="Read a complete editable menu item")
def read_menu_item(
    slug: str,
    session: SessionDep,
    _: MenuEditorDep,
    location_id: UUID | None = None,
) -> AdminMenuItemResponse:
    item = get_menu_item(session, slug)
    location = (
        get_location(session, location_id)
        if location_id
        else get_default_location(session)
    )
    return serialize_menu_item(
        item,
        availability=menu_item_availability(session, [item.id], location.id).get(
            item.id
        ),
        location_id=location.id,
        allergens=menu_item_allergens(session, [item.id]).get(item.id, []),
        history=menu_item_history(session, item.id),
    )


@router.post(
    "", status_code=status.HTTP_201_CREATED, summary="Create an editable menu item"
)
def create_menu_item(
    request: MenuItemWriteRequest, session: SessionDep, actor: MenuEditorDep
) -> AdminMenuItemResponse:
    if (
        session.scalar(select(MenuItem.id).where(MenuItem.slug == request.slug))
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That menu item URL is already in use.",
        )
    item = MenuItem(
        category_id=request.category_id,
        media_id=request.media_id,
        name=request.name.strip(),
        slug=request.slug,
        description=request.description.strip(),
        base_price_minor=request.base_price_minor,
    )
    session.add(item)
    session.flush()
    write_menu_item(session, item, request, actor, action=CatalogChangeAction.CREATED)
    session.commit()
    session.expire_all()
    return read_menu_item(item.slug, session, actor, request.availability.location_id)


@router.put("/{slug}", summary="Replace one editable menu item")
def update_menu_item(
    slug: str,
    request: MenuItemWriteRequest,
    session: SessionDep,
    actor: MenuEditorDep,
) -> AdminMenuItemResponse:
    item = get_menu_item(session, slug)
    existing_id = session.scalar(
        select(MenuItem.id).where(MenuItem.slug == request.slug)
    )
    if existing_id is not None and existing_id != item.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That menu item URL is already in use.",
        )
    write_menu_item(session, item, request, actor, action=CatalogChangeAction.UPDATED)
    session.commit()
    session.expire_all()
    return read_menu_item(item.slug, session, actor, request.availability.location_id)


@router.patch(
    "/{slug}/availability", summary="Change availability without editing the whole item"
)
def update_availability(
    slug: str,
    request: MenuAvailabilityRequest,
    session: SessionDep,
    actor: MenuEditorDep,
) -> AdminMenuItemResponse:
    item = get_menu_item(session, slug)
    location = get_location(session, request.location_id)
    availability = session.scalar(
        select(MenuItemAvailability).where(
            MenuItemAvailability.location_id == location.id,
            MenuItemAvailability.menu_item_id == item.id,
        )
    )
    if availability is None:
        availability = MenuItemAvailability(
            location_id=location.id, menu_item_id=item.id
        )
        session.add(availability)
    availability.state = request.state
    availability.available_from = request.available_from
    availability.available_until = request.available_until
    record_change(
        session,
        actor,
        entity_type="menu_item",
        entity_id=item.id,
        action=CatalogChangeAction.AVAILABILITY_CHANGED,
        snapshot={
            "name": item.name,
            "state": availability.state.value,
            "location": location.slug,
        },
    )
    session.commit()
    session.expire_all()
    return read_menu_item(item.slug, session, actor, location.id)
