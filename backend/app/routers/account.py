from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionDep
from app.models import (
    Category,
    CustomerAddress,
    CustomerFavorite,
    Location,
    MenuItem,
    Order,
    PublicationState,
    User,
)
from app.routers.auth import serialize_current_user
from app.schemas.account import (
    CustomerAddressCreateRequest,
    CustomerAddressResponse,
    CustomerAddressUpdateRequest,
    CustomerFavoriteResponse,
    CustomerOrderHistoryLineResponse,
    CustomerOrderHistoryResponse,
    CustomerProfileUpdateRequest,
    CustomerReorderResponse,
)
from app.schemas.auth import CurrentUserResponse
from app.schemas.cart import CartLineRequest
from app.services.auth import CustomerCurrentUserDep
from app.services.cart import media_summary, quote_cart

router = APIRouter(prefix="/api/v1/account", tags=["Customer account"])


def not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="We could not find that item in your account.",
    )


def serialize_address(address: CustomerAddress) -> CustomerAddressResponse:
    return CustomerAddressResponse(
        id=address.id,
        label=address.label,
        recipient_name=address.recipient_name,
        phone=address.phone,
        address_text=address.address_text,
        is_default=address.is_default,
    )


def lock_customer(session: SessionDep, user_id: UUID) -> None:
    session.scalar(select(User.id).where(User.id == user_id).with_for_update())


def make_default_if_needed(
    session: SessionDep, user_id: UUID, address: CustomerAddress, requested: bool
) -> None:
    """Keep one default address per customer under a user-row lock."""

    lock_customer(session, user_id)
    current_default = session.scalar(
        select(CustomerAddress.id)
        .where(
            CustomerAddress.user_id == user_id,
            CustomerAddress.is_default.is_(True),
        )
        .with_for_update()
    )
    if requested or current_default is None:
        session.execute(
            update(CustomerAddress)
            .where(
                CustomerAddress.user_id == user_id,
                CustomerAddress.id != address.id,
            )
            .values(is_default=False)
        )
        address.is_default = True


def commit_or_address_conflict(session: SessionDep) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An address already uses this label.",
        ) from None


@router.get("/profile", response_model=CurrentUserResponse)
def read_profile(current_user: CustomerCurrentUserDep) -> CurrentUserResponse:
    return serialize_current_user(current_user)


@router.patch("/profile", response_model=CurrentUserResponse)
def update_profile(
    request: CustomerProfileUpdateRequest,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CurrentUserResponse:
    if request.email is not None:
        current_user.email = str(request.email).lower()
    if request.display_name is not None:
        current_user.display_name = request.display_name
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses this email address.",
        ) from None
    return serialize_current_user(current_user)


@router.get("/addresses", response_model=list[CustomerAddressResponse])
def list_addresses(
    session: SessionDep, current_user: CustomerCurrentUserDep
) -> list[CustomerAddressResponse]:
    addresses = session.scalars(
        select(CustomerAddress)
        .where(CustomerAddress.user_id == current_user.id)
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
    ).all()
    return [serialize_address(address) for address in addresses]


@router.post(
    "/addresses",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_address(
    request: CustomerAddressCreateRequest,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerAddressResponse:
    address_values = request.model_dump()
    requested_default = address_values.pop("is_default")
    address = CustomerAddress(
        user_id=current_user.id, is_default=False, **address_values
    )
    session.add(address)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An address already uses this label.",
        ) from None
    make_default_if_needed(session, current_user.id, address, requested_default)
    commit_or_address_conflict(session)
    return serialize_address(address)


@router.patch("/addresses/{address_id}", response_model=CustomerAddressResponse)
def update_address(
    address_id: UUID,
    request: CustomerAddressUpdateRequest,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerAddressResponse:
    address = session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.user_id == current_user.id,
        )
    )
    if address is None:
        raise not_found()
    changed = request.model_dump(exclude_unset=True)
    requested_default = changed.pop("is_default", None)
    for name, value in changed.items():
        setattr(address, name, value)
    if requested_default is True:
        make_default_if_needed(session, current_user.id, address, True)
    commit_or_address_conflict(session)
    return serialize_address(address)


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: UUID,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> Response:
    address = session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.user_id == current_user.id,
        )
    )
    if address is None:
        raise not_found()
    was_default = address.is_default
    lock_customer(session, current_user.id)
    session.delete(address)
    session.flush()
    if was_default:
        replacement = session.scalar(
            select(CustomerAddress)
            .where(CustomerAddress.user_id == current_user.id)
            .order_by(CustomerAddress.created_at.desc())
            .limit(1)
        )
        if replacement is not None:
            replacement.is_default = True
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def serialize_favorite(favorite: CustomerFavorite) -> CustomerFavoriteResponse:
    item = favorite.menu_item
    return CustomerFavoriteResponse(
        id=favorite.id,
        slug=item.slug,
        name=item.name,
        description=item.description,
        final_price_minor=item.base_price_minor - item.demo_discount_minor,
        currency_code=item.currency_code,
        media=media_summary(item.media),
        is_available=(
            item.publication_state == PublicationState.PUBLISHED
            and item.category.is_published
        ),
    )


@router.get("/favorites", response_model=list[CustomerFavoriteResponse])
def list_favorites(
    session: SessionDep, current_user: CustomerCurrentUserDep
) -> list[CustomerFavoriteResponse]:
    favorites = session.scalars(
        select(CustomerFavorite)
        .where(CustomerFavorite.user_id == current_user.id)
        .options(
            joinedload(CustomerFavorite.menu_item).joinedload(MenuItem.category),
            joinedload(CustomerFavorite.menu_item).joinedload(MenuItem.media),
        )
        .order_by(CustomerFavorite.created_at.desc())
    ).all()
    return [serialize_favorite(favorite) for favorite in favorites]


@router.put("/favorites/{menu_item_slug}", response_model=CustomerFavoriteResponse)
def save_favorite(
    menu_item_slug: Annotated[str, Path(pattern=r"^[a-z0-9-]+$")],
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerFavoriteResponse:
    item = session.scalar(
        select(MenuItem)
        .join(MenuItem.category)
        .where(
            MenuItem.slug == menu_item_slug,
            MenuItem.publication_state == PublicationState.PUBLISHED,
            Category.is_published.is_(True),
        )
        .options(joinedload(MenuItem.category), joinedload(MenuItem.media))
    )
    if item is None:
        raise not_found()
    favorite = session.scalar(
        select(CustomerFavorite)
        .where(
            CustomerFavorite.user_id == current_user.id,
            CustomerFavorite.menu_item_id == item.id,
        )
        .options(
            joinedload(CustomerFavorite.menu_item).joinedload(MenuItem.category),
            joinedload(CustomerFavorite.menu_item).joinedload(MenuItem.media),
        )
    )
    if favorite is None:
        favorite = CustomerFavorite(user_id=current_user.id, menu_item_id=item.id)
        session.add(favorite)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            favorite = session.scalar(
                select(CustomerFavorite)
                .where(
                    CustomerFavorite.user_id == current_user.id,
                    CustomerFavorite.menu_item_id == item.id,
                )
                .options(
                    joinedload(CustomerFavorite.menu_item).joinedload(
                        MenuItem.category
                    ),
                    joinedload(CustomerFavorite.menu_item).joinedload(MenuItem.media),
                )
            )
            if favorite is None:
                raise
    return serialize_favorite(favorite)


@router.delete("/favorites/{menu_item_slug}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    menu_item_slug: Annotated[str, Path(pattern=r"^[a-z0-9-]+$")],
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> Response:
    favorite = session.scalar(
        select(CustomerFavorite)
        .join(CustomerFavorite.menu_item)
        .where(
            CustomerFavorite.user_id == current_user.id,
            MenuItem.slug == menu_item_slug,
        )
    )
    if favorite is None:
        raise not_found()
    session.delete(favorite)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def serialize_account_order(order: Order) -> CustomerOrderHistoryResponse:
    fulfillment = order.fulfillment_snapshot
    return CustomerOrderHistoryResponse(
        public_reference=order.public_reference,
        created_at=order.created_at,
        status=str(order.status),
        fulfillment_method=str(order.fulfillment_method),
        location_name=str(fulfillment.get("location_name", order.location.name)),
        currency_code=order.currency_code,
        total_minor=order.total_minor,
        lines=[
            CustomerOrderHistoryLineResponse(
                menu_item_slug=item.menu_item_slug,
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                selected_option_names=[
                    str(option["name"])
                    for option in item.selected_options_snapshot
                    if isinstance(option, dict) and isinstance(option.get("name"), str)
                ],
            )
            for item in order.items
        ],
    )


@router.get("/orders", response_model=list[CustomerOrderHistoryResponse])
def list_order_history(
    session: SessionDep, current_user: CustomerCurrentUserDep
) -> list[CustomerOrderHistoryResponse]:
    orders = session.scalars(
        select(Order)
        .where(Order.customer_id == current_user.id)
        .options(joinedload(Order.location), selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .limit(50)
    ).all()
    return [serialize_account_order(order) for order in orders]


@router.post(
    "/orders/{public_reference}/reorder", response_model=CustomerReorderResponse
)
def reorder_customer_order(
    public_reference: Annotated[str, Path(pattern=r"^N-[0-9A-F]{16}$")],
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerReorderResponse:
    order = session.scalar(
        select(Order)
        .where(
            Order.public_reference == public_reference,
            Order.customer_id == current_user.id,
        )
        .options(joinedload(Order.location), selectinload(Order.items))
    )
    if order is None:
        raise not_found()
    location = session.scalar(
        select(Location)
        .where(Location.id == order.location_id, Location.is_published.is_(True))
        .with_for_update()
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This order's kitchen location is not available for reorder.",
        )
    lines = [
        CartLineRequest(
            client_line_id=f"reorder_{item.id.hex}",
            menu_item_slug=item.menu_item_slug,
            quantity=item.quantity,
            option_ids=[option["id"] for option in item.selected_options_snapshot],
            note=item.note,
        )
        for item in order.items
    ]
    quote = quote_cart(session, lines, location)
    return CustomerReorderResponse(
        location_slug=location.slug, lines=lines, quote=quote
    )
