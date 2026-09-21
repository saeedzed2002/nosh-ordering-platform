from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FulfillmentMethod, Order, OrderStatus, OrderStatusEvent, User
from app.schemas.orders import OrderIssueReason, OrderStatusTransitionRequest
from app.services.checkout import order_by_public_reference

TERMINAL_STATUSES = {
    OrderStatus.HANDED_TO_CUSTOMER,
    OrderStatus.DELIVERED,
    OrderStatus.DECLINED,
    OrderStatus.CANCELLED,
}
ISSUE_STATUSES = {
    OrderStatus.DECLINED,
    OrderStatus.CANCELLED,
    OrderStatus.NEEDS_CONTACT,
}

NORMAL_TRANSITIONS = {
    FulfillmentMethod.PICKUP: {
        OrderStatus.SUBMITTED: {OrderStatus.ACCEPTED},
        OrderStatus.ACCEPTED: {OrderStatus.PREPARING},
        OrderStatus.PREPARING: {OrderStatus.READY_FOR_PICKUP},
        OrderStatus.READY_FOR_PICKUP: {OrderStatus.HANDED_TO_CUSTOMER},
    },
    FulfillmentMethod.DELIVERY: {
        OrderStatus.SUBMITTED: {OrderStatus.ACCEPTED},
        OrderStatus.ACCEPTED: {OrderStatus.PREPARING},
        OrderStatus.PREPARING: {OrderStatus.READY_FOR_COURIER},
        OrderStatus.READY_FOR_COURIER: {OrderStatus.HANDED_TO_COURIER},
        OrderStatus.HANDED_TO_COURIER: {OrderStatus.OUT_FOR_DELIVERY},
        OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    },
}

STATUS_NOTES = {
    OrderStatus.ACCEPTED: "The kitchen has accepted this order.",
    OrderStatus.PREPARING: "The kitchen has started preparing this order.",
    OrderStatus.READY_FOR_PICKUP: "This order is ready to collect from the kitchen.",
    OrderStatus.READY_FOR_COURIER: "This order is ready to hand to the courier.",
    OrderStatus.HANDED_TO_CUSTOMER: "This order has been collected from the kitchen.",
    OrderStatus.HANDED_TO_COURIER: "This order has been handed to the courier.",
    OrderStatus.OUT_FOR_DELIVERY: (
        "This order is on its way. The local demo does not use live courier tracking."
    ),
    OrderStatus.DELIVERED: "This order has been marked as delivered.",
}
ISSUE_REASON_NOTES = {
    OrderIssueReason.CUSTOMER_REQUEST: "a customer request",
    OrderIssueReason.FULFILLMENT_DETAILS: "a fulfilment detail",
    OrderIssueReason.KITCHEN_UNAVAILABLE: "kitchen availability",
    OrderIssueReason.SCHEDULE_UNAVAILABLE: "the requested time",
}


def preparation_minutes(order: Order) -> int:
    value = order.fulfillment_snapshot.get(
        "preparation_minutes", order.location.preparation_minutes
    )
    return int(value)


def valid_next_statuses(order: Order) -> set[OrderStatus]:
    current = OrderStatus(order.status)
    if current in TERMINAL_STATUSES:
        return set()
    if current == OrderStatus.NEEDS_CONTACT:
        return {OrderStatus.ACCEPTED, OrderStatus.CANCELLED}
    if current == OrderStatus.SCHEDULED:
        return {
            OrderStatus.ACCEPTED,
            OrderStatus.PREPARING,
            OrderStatus.DECLINED,
            OrderStatus.CANCELLED,
            OrderStatus.NEEDS_CONTACT,
        }
    fulfillment_method = FulfillmentMethod(order.fulfillment_method)
    return NORMAL_TRANSITIONS[fulfillment_method].get(current, set()) | ISSUE_STATUSES


def issue_note(status_value: OrderStatus, reason: OrderIssueReason) -> str:
    reason_note = ISSUE_REASON_NOTES[reason]
    if status_value == OrderStatus.NEEDS_CONTACT:
        return f"The kitchen needs to confirm {reason_note} before continuing."
    if status_value == OrderStatus.DECLINED:
        return f"The kitchen cannot accept this order because of {reason_note}."
    return f"This order was cancelled because of {reason_note}."


def assert_scheduled_order_is_released_at_the_right_time(
    order: Order, target_status: OrderStatus
) -> None:
    if OrderStatus(order.status) != OrderStatus.SCHEDULED:
        return
    if target_status not in {OrderStatus.ACCEPTED, OrderStatus.PREPARING}:
        return
    if order.scheduled_for is None:
        return
    scheduled_for = order.scheduled_for
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=UTC)
    release_at = scheduled_for - timedelta(minutes=preparation_minutes(order))
    if datetime.now(UTC) < release_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This scheduled order cannot enter the kitchen preparation window yet."
            ),
        )


def transition_order_status(
    session: Session,
    public_reference: str,
    request: OrderStatusTransitionRequest,
    actor: User,
) -> Order:
    order = session.scalar(
        select(Order)
        .where(Order.public_reference == public_reference)
        .with_for_update()
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that order.",
        )

    target_status = request.status
    if target_status not in valid_next_statuses(order):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That status is not a valid next step for this order.",
        )
    assert_scheduled_order_is_released_at_the_right_time(order, target_status)

    note = (
        issue_note(target_status, request.reason)
        if target_status in ISSUE_STATUSES and request.reason is not None
        else STATUS_NOTES[target_status]
    )
    order.status = target_status
    session.add(
        OrderStatusEvent(
            order_id=order.id,
            actor_id=actor.id,
            created_at=datetime.now(UTC),
            status=target_status,
            note=note,
        )
    )
    session.commit()
    session.expire_all()
    refreshed = order_by_public_reference(session, public_reference)
    if refreshed is None:
        raise RuntimeError("Order disappeared after a committed status transition.")
    return refreshed
