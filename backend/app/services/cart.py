from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    AvailabilityState,
    Category,
    Location,
    MediaAsset,
    MenuItem,
    MenuItemAvailability,
    OptionGroup,
    PublicationState,
)
from app.schemas.cart import (
    CartLineRequest,
    CartQuoteLineResponse,
    CartQuoteResponse,
    CartSelectedOptionResponse,
)
from app.schemas.catalog import MediaSummary


def media_summary(media: MediaAsset | None) -> MediaSummary | None:
    if media is None:
        return None
    return MediaSummary(
        id=media.id,
        alt_text=media.alt_text,
        width=media.width,
        height=media.height,
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


def availability_by_menu_item_id(
    session: Session, items: list[MenuItem], location: Location | None
) -> dict[UUID, AvailabilityState]:
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


def quote_cart(
    session: Session, lines: list[CartLineRequest], location: Location | None
) -> CartQuoteResponse:
    """Recalculate a browser cart from published kitchen data only."""

    item_slugs = [line.menu_item_slug for line in lines]
    items = session.scalars(
        select(MenuItem)
        .join(MenuItem.category)
        .where(
            MenuItem.slug.in_(item_slugs),
            MenuItem.publication_state == PublicationState.PUBLISHED,
            Category.is_published.is_(True),
        )
        .options(
            joinedload(MenuItem.media),
            selectinload(MenuItem.option_groups).selectinload(OptionGroup.options),
        )
    ).all()
    items_by_slug = {item.slug: item for item in items}
    availability = availability_by_menu_item_id(session, items, location)

    quoted_lines: list[CartQuoteLineResponse] = []
    subtotal_minor = 0
    currency_code: str | None = None

    for line in lines:
        item = items_by_slug.get(line.menu_item_slug)
        if item is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A dish in this cart is no longer on the published menu.",
            )
        if availability.get(item.id) != AvailabilityState.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{item.name} is not available from the kitchen right now.",
            )

        selected_option_ids = set(line.option_ids)
        selectable_options = {
            option.id: (option_group, option)
            for option_group in item.option_groups
            for option in option_group.options
            if option.is_available
        }
        if selected_option_ids.difference(selectable_options):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "One of the selected choices is no longer available for this dish."
                ),
            )

        selected_options: list[CartSelectedOptionResponse] = []
        option_total_minor = 0
        for option_group in sorted(
            item.option_groups, key=lambda group: group.display_order
        ):
            selections = [
                option
                for option in option_group.options
                if option.id in selected_option_ids and option.is_available
            ]
            selection_count = len(selections)
            if (
                not option_group.minimum_selections
                <= selection_count
                <= option_group.maximum_selections
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"{option_group.name} needs between "
                        f"{option_group.minimum_selections} and "
                        f"{option_group.maximum_selections} selection(s)."
                    ),
                )
            for option in sorted(selections, key=lambda choice: choice.display_order):
                option_total_minor += option.price_delta_minor
                selected_options.append(
                    CartSelectedOptionResponse(
                        id=option.id,
                        name=option.name,
                        option_group_name=option_group.name,
                        price_delta_minor=option.price_delta_minor,
                    )
                )

        if currency_code is not None and currency_code != item.currency_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This local demo cart supports one currency at a time.",
            )
        currency_code = item.currency_code
        unit_price_minor = (
            item.base_price_minor - item.demo_discount_minor + option_total_minor
        )
        line_total_minor = unit_price_minor * line.quantity
        subtotal_minor += line_total_minor
        quoted_lines.append(
            CartQuoteLineResponse(
                client_line_id=line.client_line_id,
                menu_item_slug=item.slug,
                name=item.name,
                media=media_summary(item.media),
                quantity=line.quantity,
                note=line.note,
                selected_options=selected_options,
                unit_price_minor=unit_price_minor,
                line_total_minor=line_total_minor,
                currency_code=item.currency_code,
            )
        )

    return CartQuoteResponse(
        lines=quoted_lines,
        subtotal_minor=subtotal_minor,
        currency_code=currency_code or "USD",
    )
