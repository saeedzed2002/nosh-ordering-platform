from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Location, OnlineOrderingState, Order, OrderStatus

CAPACITY_CONSUMING_STATUSES = {
    OrderStatus.SUBMITTED,
    OrderStatus.ACCEPTED,
    OrderStatus.PREPARING,
    OrderStatus.READY_FOR_PICKUP,
    OrderStatus.READY_FOR_COURIER,
    OrderStatus.HANDED_TO_COURIER,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.NEEDS_CONTACT,
}


@dataclass(frozen=True)
class OrderingAvailability:
    is_available: bool
    message: str
    state: OnlineOrderingState


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def ordering_availability(
    location: Location, now: datetime | None = None
) -> OrderingAvailability:
    current_time = now or datetime.now(UTC)
    configured_state = OnlineOrderingState(location.online_ordering_state)
    pause_until = as_utc(location.online_ordering_paused_until)
    if configured_state == OnlineOrderingState.OFF:
        return OrderingAvailability(
            is_available=False,
            state=configured_state,
            message="Online ordering is unavailable from this kitchen right now.",
        )
    if configured_state == OnlineOrderingState.TIMED_PAUSE and (
        pause_until is None or pause_until > current_time
    ):
        until_copy = (
            pause_until.strftime("%b %d, %Y at %H:%M UTC")
            if pause_until is not None
            else "a later time"
        )
        return OrderingAvailability(
            is_available=False,
            state=configured_state,
            message=f"Online ordering is paused until {until_copy}.",
        )
    return OrderingAvailability(
        is_available=True,
        state=OnlineOrderingState.ON,
        message="Online ordering is available from this kitchen.",
    )


def require_online_ordering(location: Location) -> None:
    availability = ordering_availability(location)
    if not availability.is_available:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=availability.message,
        )


def require_demo_capacity(session: Session, location: Location) -> None:
    """Reject a new immediate order once the kitchen's demo active-order limit is full.

    Checkout locks the location row before calling this function, so concurrent
    checkouts for the same kitchen cannot both consume its final available slot.
    """

    active_order_count = session.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.location_id == location.id,
            Order.status.in_(CAPACITY_CONSUMING_STATUSES),
        )
    )
    if (active_order_count or 0) >= location.demo_capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Online ordering has reached this kitchen's current demo capacity. "
                "Please choose another time or try again later."
            ),
        )
