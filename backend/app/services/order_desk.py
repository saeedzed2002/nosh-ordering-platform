from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Allergen,
    FulfillmentMethod,
    Location,
    MenuItemAllergen,
    OnlineOrderingState,
    Order,
    OrderStatus,
    OrderStatusEvent,
)
from app.schemas.admin_orders import (
    AdminOrderAllergenResponse,
    AdminOrderDetailResponse,
    AdminOrderLineResponse,
    AdminOrderListItemResponse,
    AdminOrderLocationReference,
    AdminOrderQueueCount,
    AdminOrderStatusEventResponse,
    LocationOrderControlsRequest,
    LocationOrderControlsResponse,
    OrderDeskQueue,
)
from app.services.order_lifecycle import valid_next_statuses
from app.services.ordering import ordering_availability

QUEUE_LABELS = {
    OrderDeskQueue.NEEDS_APPROVAL: "Needs approval",
    OrderDeskQueue.SCHEDULED: "Scheduled",
    OrderDeskQueue.ACTIVE: "Active",
    OrderDeskQueue.READY: "Ready",
    OrderDeskQueue.COMPLETED: "Completed",
    OrderDeskQueue.ARCHIVE: "Archive",
}
TERMINAL_STATUSES = {
    OrderStatus.HANDED_TO_CUSTOMER,
    OrderStatus.DELIVERED,
    OrderStatus.DECLINED,
    OrderStatus.CANCELLED,
}
STATUS_SEQUENCE = list(OrderStatus)


def queue_for_status(order_status: OrderStatus) -> OrderDeskQueue:
    if order_status == OrderStatus.SUBMITTED:
        return OrderDeskQueue.NEEDS_APPROVAL
    if order_status == OrderStatus.SCHEDULED:
        return OrderDeskQueue.SCHEDULED
    if order_status in {OrderStatus.READY_FOR_PICKUP, OrderStatus.READY_FOR_COURIER}:
        return OrderDeskQueue.READY
    if order_status in TERMINAL_STATUSES:
        return OrderDeskQueue.COMPLETED
    return OrderDeskQueue.ACTIVE


def order_statement():
    return select(Order).options(
        joinedload(Order.location),
        selectinload(Order.items),
        selectinload(Order.status_events).joinedload(OrderStatusEvent.actor),
    )


def list_orders(
    session: Session,
    *,
    query: str | None,
    queue: OrderDeskQueue | None,
    status_value: OrderStatus | None,
    location_id: UUID | None,
    fulfillment_method: FulfillmentMethod | None,
    starts_at: datetime | None,
    ends_at: datetime | None,
) -> tuple[list[Order], list[AdminOrderQueueCount]]:
    statement = order_statement().order_by(Order.created_at.desc())
    if status_value is not None:
        statement = statement.where(Order.status == status_value)
    if location_id is not None:
        statement = statement.where(Order.location_id == location_id)
    if fulfillment_method is not None:
        statement = statement.where(Order.fulfillment_method == fulfillment_method)
    if starts_at is not None:
        statement = statement.where(Order.created_at >= starts_at)
    if ends_at is not None:
        statement = statement.where(Order.created_at < ends_at)

    orders = session.scalars(statement).all()
    phrase = query.strip().casefold() if query else ""
    if phrase:
        orders = [
            order
            for order in orders
            if phrase in order.public_reference.casefold()
            or phrase in str(order.recipient_snapshot.get("name", "")).casefold()
            or phrase in str(order.recipient_snapshot.get("email", "")).casefold()
        ]

    queue_counts = [
        AdminOrderQueueCount(
            queue=entry,
            label=QUEUE_LABELS[entry],
            count=sum(
                queue_for_status(OrderStatus(order.status)) == entry for order in orders
            ),
        )
        for entry in (
            OrderDeskQueue.NEEDS_APPROVAL,
            OrderDeskQueue.SCHEDULED,
            OrderDeskQueue.ACTIVE,
            OrderDeskQueue.READY,
            OrderDeskQueue.COMPLETED,
        )
    ]
    if queue == OrderDeskQueue.ARCHIVE:
        orders = [
            order for order in orders if OrderStatus(order.status) in TERMINAL_STATUSES
        ]
    elif queue is not None:
        orders = [
            order
            for order in orders
            if queue_for_status(OrderStatus(order.status)) == queue
        ]
    return orders, queue_counts


def serialize_order_list_item(order: Order) -> AdminOrderListItemResponse:
    return AdminOrderListItemResponse(
        public_reference=order.public_reference,
        status=OrderStatus(order.status),
        fulfillment_method=FulfillmentMethod(order.fulfillment_method),
        created_at=order.created_at,
        scheduled_for=order.scheduled_for,
        location_name=order.location.name,
        recipient_name=str(order.recipient_snapshot.get("name", "Customer")),
        total_minor=order.total_minor,
        currency_code=order.currency_code,
        item_count=sum(item.quantity for item in order.items),
        queue=queue_for_status(OrderStatus(order.status)),
    )


def allergens_by_menu_item_id(
    session: Session, menu_item_ids: list[UUID]
) -> dict[UUID, list[AdminOrderAllergenResponse]]:
    if not menu_item_ids:
        return {}
    rows = session.execute(
        select(MenuItemAllergen.menu_item_id, Allergen)
        .join(Allergen, Allergen.id == MenuItemAllergen.allergen_id)
        .where(MenuItemAllergen.menu_item_id.in_(menu_item_ids))
    ).all()
    result: dict[UUID, list[AdminOrderAllergenResponse]] = {}
    for menu_item_id, allergen in rows:
        result.setdefault(menu_item_id, []).append(
            AdminOrderAllergenResponse(name=allergen.name, slug=allergen.slug)
        )
    return result


def order_detail(session: Session, public_reference: str) -> AdminOrderDetailResponse:
    order = session.scalar(
        order_statement().where(Order.public_reference == public_reference)
    )
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that order.",
        )
    current_allergens = allergens_by_menu_item_id(
        session, [item.menu_item_id for item in order.items]
    )
    summary = serialize_order_list_item(order)
    return AdminOrderDetailResponse(
        **summary.model_dump(),
        recipient_email=str(order.recipient_snapshot.get("email", "")),
        recipient_phone=str(order.recipient_snapshot.get("phone", "")),
        delivery_address=order.fulfillment_snapshot.get("delivery_address"),
        fulfillment_instructions=order.fulfillment_snapshot.get("instructions"),
        pickup_instructions=order.fulfillment_snapshot.get("pickup_instructions"),
        delivery_area=order.fulfillment_snapshot.get("delivery_area"),
        lines=[
            AdminOrderLineResponse(
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                note=item.note,
                selected_options=[
                    str(option["name"]) for option in item.selected_options_snapshot
                ],
                ingredients=[
                    str(value) for value in item.item_snapshot.get("ingredients", [])
                ],
                dietary_tags=[
                    str(value) for value in item.item_snapshot.get("dietary_tags", [])
                ],
                allergens=[
                    AdminOrderAllergenResponse.model_validate(allergen)
                    for allergen in item.item_snapshot.get(
                        "allergens", current_allergens.get(item.menu_item_id, [])
                    )
                ],
            )
            for item in order.items
        ],
        status_events=[
            AdminOrderStatusEventResponse(
                status=OrderStatus(event.status),
                note=event.note,
                created_at=event.created_at,
                actor_name=event.actor.display_name
                if event.actor is not None
                else None,
            )
            for event in sorted(order.status_events, key=lambda event: event.created_at)
        ],
        valid_next_statuses=sorted(
            valid_next_statuses(order), key=lambda value: STATUS_SEQUENCE.index(value)
        ),
    )


def location_controls_response(location: Location) -> LocationOrderControlsResponse:
    availability = ordering_availability(location)
    return LocationOrderControlsResponse(
        id=location.id,
        name=location.name,
        online_ordering_state=OnlineOrderingState(location.online_ordering_state),
        online_ordering_paused_until=location.online_ordering_paused_until,
        ordering_available=availability.is_available,
        ordering_message=availability.message,
        preparation_minutes=location.preparation_minutes,
        demo_capacity=location.demo_capacity,
    )


def update_location_controls(
    session: Session, location_id: UUID, request: LocationOrderControlsRequest
) -> LocationOrderControlsResponse:
    location = session.scalar(
        select(Location).where(Location.id == location_id).with_for_update()
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that kitchen location.",
        )
    location.online_ordering_state = request.online_ordering_state
    location.online_ordering_paused_until = request.online_ordering_paused_until
    location.preparation_minutes = request.preparation_minutes
    location.demo_capacity = request.demo_capacity
    session.commit()
    session.refresh(location)
    return location_controls_response(location)


def location_references(session: Session) -> list[AdminOrderLocationReference]:
    return [
        AdminOrderLocationReference(id=location.id, name=location.name)
        for location in session.scalars(select(Location).order_by(Location.name)).all()
    ]


def all_location_controls(session: Session) -> list[LocationOrderControlsResponse]:
    return [
        location_controls_response(location)
        for location in session.scalars(select(Location).order_by(Location.name)).all()
    ]
