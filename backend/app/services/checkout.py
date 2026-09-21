from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    FulfillmentMethod,
    Location,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    Promotion,
    PromotionKind,
)
from app.schemas.orders import (
    CheckoutRequest,
    CheckoutTiming,
    FulfillmentMethodRequest,
    OrderReceiptLineResponse,
    OrderReceiptOptionResponse,
    OrderReceiptResponse,
    OrderStatusEventResponse,
    PaymentScenario,
)
from app.services.cart import quote_cart


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def request_fingerprint(request: CheckoutRequest) -> str:
    payload = request.model_dump(mode="json", exclude={"idempotency_key"})
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def order_query():
    return select(Order).options(
        joinedload(Order.location),
        selectinload(Order.items),
        selectinload(Order.status_events),
    )


def order_by_idempotency_key(session: Session, key: str) -> Order | None:
    return session.scalar(order_query().where(Order.idempotency_key == key))


def order_by_public_reference(session: Session, reference: str) -> Order | None:
    return session.scalar(order_query().where(Order.public_reference == reference))


def resolve_checkout_location(session: Session, request: CheckoutRequest) -> Location:
    location = session.scalar(
        select(Location).where(
            Location.slug == request.location_slug,
            Location.is_published.is_(True),
        )
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that location for checkout.",
        )
    if (
        request.fulfillment_method == FulfillmentMethodRequest.PICKUP
        and not location.pickup_available
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pickup is not available from this location right now.",
        )
    if (
        request.fulfillment_method == FulfillmentMethodRequest.DELIVERY
        and not location.delivery_available
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delivery is not available from this location right now.",
        )
    return location


def resolve_promotion(
    session: Session, code: str | None, subtotal_minor: int, now: datetime
) -> tuple[Promotion | None, int]:
    if code is None:
        return None, 0
    promotion = session.scalar(
        select(Promotion).where(Promotion.code == code).with_for_update()
    )
    if promotion is None or not promotion.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That promotion is not active.",
        )
    starts_at = as_utc(promotion.starts_at)
    ends_at = as_utc(promotion.ends_at)
    if (starts_at is not None and now < starts_at) or (
        ends_at is not None and now >= ends_at
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That promotion is not valid at this time.",
        )
    if subtotal_minor < promotion.minimum_order_minor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("That promotion needs a larger order before it can be applied."),
        )
    if (
        promotion.usage_limit is not None
        and promotion.usage_count >= promotion.usage_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That promotion has reached its demo usage limit.",
        )
    if promotion.kind == PromotionKind.PERCENTAGE:
        discount_minor = subtotal_minor * promotion.discount_value // 10000
    else:
        discount_minor = promotion.discount_value
    return promotion, min(discount_minor, subtotal_minor)


def validate_scheduled_time(request: CheckoutRequest, now: datetime) -> datetime | None:
    scheduled_for = as_utc(request.scheduled_for)
    if request.timing == CheckoutTiming.SCHEDULED:
        if scheduled_for is None or scheduled_for <= now:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Choose a future scheduled time for this order.",
            )
        return scheduled_for
    return None


def menu_items_for_snapshot(
    session: Session, request: CheckoutRequest
) -> dict[str, MenuItem]:
    items = session.scalars(
        select(MenuItem)
        .where(MenuItem.slug.in_([line.menu_item_slug for line in request.lines]))
        .options(joinedload(MenuItem.category))
    ).all()
    return {item.slug: item for item in items}


def public_reference() -> str:
    return f"N-{uuid4().hex[:16].upper()}"


def create_order(session: Session, request: CheckoutRequest) -> tuple[Order, bool]:
    fingerprint = request_fingerprint(request)
    existing = order_by_idempotency_key(session, request.idempotency_key)
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This checkout key has already been used for a different order.",
            )
        return existing, True

    now = datetime.now(UTC)
    location = resolve_checkout_location(session, request)
    scheduled_for = validate_scheduled_time(request, now)
    quote = quote_cart(session, request.lines, location)
    promotion, promotion_discount_minor = resolve_promotion(
        session, request.promotion_code, quote.subtotal_minor, now
    )
    if request.payment_scenario == PaymentScenario.FAILS:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                "The local mock payment was declined. "
                "No order or payment data was saved."
            ),
        )

    items_by_slug = menu_items_for_snapshot(session, request)
    if len(items_by_slug) != len({line.menu_item_slug for line in request.lines}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A dish changed while this order was being checked. Please try again."
            ),
        )

    order_status = (
        OrderStatus.SCHEDULED if scheduled_for is not None else OrderStatus.SUBMITTED
    )
    fulfillment_method = FulfillmentMethod(request.fulfillment_method)
    promotion_snapshot = (
        {
            "code": promotion.code,
            "name": promotion.name,
            "kind": PromotionKind(promotion.kind).value,
            "discount_minor": promotion_discount_minor,
        }
        if promotion is not None
        else {}
    )
    order = Order(
        public_reference=public_reference(),
        idempotency_key=request.idempotency_key,
        request_fingerprint=fingerprint,
        location_id=location.id,
        promotion_id=promotion.id if promotion is not None else None,
        status=order_status,
        fulfillment_method=fulfillment_method,
        scheduled_for=scheduled_for,
        recipient_snapshot={
            "name": request.recipient_name,
            "email": request.recipient_email,
            "phone": request.recipient_phone,
        },
        fulfillment_snapshot={
            "location_name": location.name,
            "location_address": location.address_text,
            "contact_phone": location.contact_phone,
            "pickup_instructions": location.pickup_instructions,
            "delivery_area": location.delivery_area_text,
            "preparation_minutes": location.preparation_minutes,
            "delivery_address": request.delivery_address,
            "instructions": request.fulfillment_instructions,
            "timing": request.timing.value,
        },
        promotion_snapshot=promotion_snapshot,
        payment_snapshot={
            "provider": "Nosh local mock payment",
            "outcome": "succeeded",
            "message": "Mock payment approved. No card data was requested or stored.",
        },
        currency_code=quote.currency_code,
        subtotal_minor=quote.subtotal_minor,
        promotion_discount_minor=promotion_discount_minor,
        total_minor=quote.subtotal_minor - promotion_discount_minor,
    )
    quote_by_client_line_id = {line.client_line_id: line for line in quote.lines}
    for request_line in request.lines:
        quoted_line = quote_by_client_line_id[request_line.client_line_id]
        menu_item = items_by_slug[request_line.menu_item_slug]
        order.items.append(
            OrderItem(
                menu_item_id=menu_item.id,
                menu_item_slug=menu_item.slug,
                menu_item_name=menu_item.name,
                quantity=quoted_line.quantity,
                note=quoted_line.note,
                unit_price_minor=quoted_line.unit_price_minor,
                line_total_minor=quoted_line.line_total_minor,
                currency_code=quoted_line.currency_code,
                item_snapshot={
                    "category_name": menu_item.category.name,
                    "description": menu_item.description,
                    "ingredients": menu_item.ingredients,
                    "dietary_tags": menu_item.dietary_tags,
                },
                selected_options_snapshot=[
                    option.model_dump(mode="json")
                    for option in quoted_line.selected_options
                ],
            )
        )
    order.status_events.append(
        OrderStatusEvent(
            created_at=datetime.now(UTC),
            status=order_status,
            note=(
                "Scheduled order confirmed with local mock payment."
                if scheduled_for is not None
                else "Order submitted with local mock payment."
            ),
        )
    )
    if promotion is not None:
        promotion.usage_count += 1

    session.add(order)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = order_by_idempotency_key(session, request.idempotency_key)
        if existing is not None and existing.request_fingerprint == fingerprint:
            return existing, True
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This checkout key has already been used for a different order.",
            ) from None
        raise
    return order, False


def serialize_order(order: Order) -> OrderReceiptResponse:
    fulfillment = order.fulfillment_snapshot
    payment = order.payment_snapshot
    promotion = order.promotion_snapshot
    preparation_minutes = int(
        fulfillment.get("preparation_minutes", order.location.preparation_minutes)
    )
    estimated_base = order.scheduled_for or order.created_at
    estimated_fulfillment_at = (
        as_utc(estimated_base)
        if order.scheduled_for is not None
        else (as_utc(estimated_base) or datetime.now(UTC))
        + timedelta(minutes=preparation_minutes)
    )
    return OrderReceiptResponse(
        public_reference=order.public_reference,
        status=OrderStatus(order.status).value,
        created_at=as_utc(order.created_at) or datetime.now(UTC),
        scheduled_for=as_utc(order.scheduled_for),
        location_name=str(fulfillment["location_name"]),
        location_address=str(fulfillment["location_address"]),
        contact_phone=str(
            fulfillment.get("contact_phone", order.location.contact_phone)
        ),
        fulfillment_method=FulfillmentMethod(order.fulfillment_method).value,
        pickup_instructions=fulfillment.get("pickup_instructions"),
        delivery_area=fulfillment.get("delivery_area"),
        preparation_minutes=preparation_minutes,
        estimated_fulfillment_at=estimated_fulfillment_at,
        currency_code=order.currency_code,
        subtotal_minor=order.subtotal_minor,
        promotion_code=promotion.get("code"),
        promotion_discount_minor=order.promotion_discount_minor,
        total_minor=order.total_minor,
        payment_message=str(payment["message"]),
        lines=[
            OrderReceiptLineResponse(
                menu_item_slug=item.menu_item_slug,
                menu_item_name=item.menu_item_name,
                quantity=item.quantity,
                note=item.note,
                unit_price_minor=item.unit_price_minor,
                line_total_minor=item.line_total_minor,
                currency_code=item.currency_code,
                selected_options=[
                    OrderReceiptOptionResponse.model_validate(option)
                    for option in item.selected_options_snapshot
                ],
            )
            for item in order.items
        ],
        status_events=[
            OrderStatusEventResponse(
                status=OrderStatus(event.status).value,
                note=event.note,
                created_at=as_utc(event.created_at) or datetime.now(UTC),
            )
            for event in sorted(order.status_events, key=lambda event: event.created_at)
        ],
    )
