from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionDep
from app.models import (
    AuditLog,
    Location,
    OperatingHour,
    Order,
    OrderItem,
    OrderStatus,
    Promotion,
    PromotionKind,
    Review,
    ReviewStatus,
    RoleCode,
    User,
)
from app.schemas.admin_operations import (
    AdminCustomerOrderResponse,
    AdminCustomerResponse,
    AdminReportResponse,
    AuditLogResponse,
    CustomerAccountStateRequest,
    PromotionResponse,
    PromotionWriteRequest,
    ReportPopularFood,
    ReportPromotionUse,
    ReportReviewModeration,
    ReportStatusDistribution,
    RestaurantSettingsResponse,
    RestaurantSettingsUpdateRequest,
)
from app.services.audit import record_audit_event
from app.services.auth import require_roles

router = APIRouter(prefix="/api/v1/admin/operations", tags=["Admin operations"])
OperationsDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]
OwnerDep = Annotated[User, Depends(require_roles(RoleCode.OWNER))]

REVENUE_EXCLUDED_STATUSES = {OrderStatus.DECLINED, OrderStatus.CANCELLED}


def operations_not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def promotion_snapshot(promotion: Promotion) -> dict[str, object]:
    return {
        "code": promotion.code,
        "name": promotion.name,
        "kind": PromotionKind(promotion.kind).value,
        "discount_value": promotion.discount_value,
        "minimum_order_minor": promotion.minimum_order_minor,
        "starts_at": promotion.starts_at.isoformat() if promotion.starts_at else None,
        "ends_at": promotion.ends_at.isoformat() if promotion.ends_at else None,
        "usage_limit": promotion.usage_limit,
        "usage_count": promotion.usage_count,
        "is_active": promotion.is_active,
    }


def serialize_promotion(promotion: Promotion) -> PromotionResponse:
    return PromotionResponse(
        id=promotion.id,
        code=promotion.code,
        name=promotion.name,
        kind=PromotionKind(promotion.kind),
        discount_value=promotion.discount_value,
        minimum_order_minor=promotion.minimum_order_minor,
        starts_at=promotion.starts_at,
        ends_at=promotion.ends_at,
        usage_limit=promotion.usage_limit,
        usage_count=promotion.usage_count,
        remaining_uses=(promotion.usage_limit - promotion.usage_count)
        if promotion.usage_limit is not None
        else None,
        is_active=promotion.is_active,
        created_at=promotion.created_at,
        updated_at=promotion.updated_at,
    )


def settings_snapshot(location: Location) -> dict[str, object]:
    return {
        "name": location.name,
        "slug": location.slug,
        "address_text": location.address_text,
        "contact_phone": location.contact_phone,
        "pickup_available": location.pickup_available,
        "delivery_available": location.delivery_available,
        "preparation_minutes": location.preparation_minutes,
        "demo_capacity": location.demo_capacity,
        "online_ordering_state": str(location.online_ordering_state),
        "online_ordering_paused_until": (
            location.online_ordering_paused_until.isoformat()
        )
        if location.online_ordering_paused_until
        else None,
        "is_published": location.is_published,
        "hours": [
            {
                "weekday": hour.weekday,
                "opens_at": hour.opens_at.isoformat() if hour.opens_at else None,
                "closes_at": hour.closes_at.isoformat() if hour.closes_at else None,
                "is_closed": hour.is_closed,
            }
            for hour in sorted(location.hours, key=lambda value: value.weekday)
        ],
    }


def serialize_settings(location: Location) -> RestaurantSettingsResponse:
    return RestaurantSettingsResponse(
        id=location.id,
        name=location.name,
        slug=location.slug,
        address_text=location.address_text,
        contact_phone=location.contact_phone,
        pickup_instructions=location.pickup_instructions,
        delivery_area_text=location.delivery_area_text,
        pickup_available=location.pickup_available,
        delivery_available=location.delivery_available,
        preparation_minutes=location.preparation_minutes,
        demo_capacity=location.demo_capacity,
        online_ordering_state=location.online_ordering_state,
        online_ordering_paused_until=location.online_ordering_paused_until,
        is_published=location.is_published,
        hours=[
            {
                "weekday": hour.weekday,
                "opens_at": hour.opens_at,
                "closes_at": hour.closes_at,
                "is_closed": hour.is_closed,
            }
            for hour in sorted(location.hours, key=lambda value: value.weekday)
        ],
    )


def customer_snapshot(user: User) -> dict[str, object]:
    return {"display_name": user.display_name, "is_active": user.is_active}


def customer_statement():
    return (
        select(User)
        .options(joinedload(User.role))
        .where(User.role.has(code=RoleCode.CUSTOMER))
    )


def serialize_customer(
    session: SessionDep, user: User, *, include_orders: bool
) -> AdminCustomerResponse:
    order_count, last_order_at = session.execute(
        select(func.count(Order.id), func.max(Order.created_at)).where(
            Order.customer_id == user.id
        )
    ).one()
    orders: list[AdminCustomerOrderResponse] = []
    if include_orders:
        orders = [
            AdminCustomerOrderResponse(
                public_reference=order.public_reference,
                status=OrderStatus(order.status),
                fulfillment_method=str(order.fulfillment_method),
                total_minor=order.total_minor,
                currency_code=order.currency_code,
                created_at=order.created_at,
            )
            for order in session.scalars(
                select(Order)
                .where(Order.customer_id == user.id)
                .order_by(Order.created_at.desc())
                .limit(25)
            ).all()
        ]
    return AdminCustomerResponse(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        order_count=int(order_count),
        last_order_at=last_order_at,
        orders=orders,
    )


def serialize_audit(event: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=event.id,
        created_at=event.created_at,
        actor_name=event.actor.display_name,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        action=event.action,
        before_snapshot=event.before_snapshot,
        after_snapshot=event.after_snapshot,
    )


@router.get("/promotions", response_model=list[PromotionResponse])
def list_promotions(session: SessionDep, _: OperationsDep) -> list[PromotionResponse]:
    promotions = session.scalars(
        select(Promotion).order_by(
            Promotion.is_active.desc(), Promotion.created_at.desc()
        )
    ).all()
    return [serialize_promotion(promotion) for promotion in promotions]


@router.post(
    "/promotions", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED
)
def create_promotion(
    request: PromotionWriteRequest,
    session: SessionDep,
    current_user: OperationsDep,
) -> PromotionResponse:
    promotion = Promotion(**request.model_dump())
    session.add(promotion)
    try:
        session.flush()
        record_audit_event(
            session,
            current_user,
            entity_type="promotion",
            entity_id=promotion.id,
            action="created",
            before_snapshot={},
            after_snapshot=promotion_snapshot(promotion),
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A promotion already uses that code.",
        ) from None
    return serialize_promotion(promotion)


@router.put("/promotions/{promotion_id}", response_model=PromotionResponse)
def update_promotion(
    promotion_id: UUID,
    request: PromotionWriteRequest,
    session: SessionDep,
    current_user: OperationsDep,
) -> PromotionResponse:
    promotion = session.scalar(
        select(Promotion).where(Promotion.id == promotion_id).with_for_update()
    )
    if promotion is None:
        raise operations_not_found("We could not find that promotion.")
    before = promotion_snapshot(promotion)
    for field, value in request.model_dump().items():
        setattr(promotion, field, value)
    record_audit_event(
        session,
        current_user,
        entity_type="promotion",
        entity_id=promotion.id,
        action="updated",
        before_snapshot=before,
        after_snapshot=promotion_snapshot(promotion),
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A promotion already uses that code.",
        ) from None
    return serialize_promotion(promotion)


@router.post("/promotions/{promotion_id}/deactivate", response_model=PromotionResponse)
def deactivate_promotion(
    promotion_id: UUID, session: SessionDep, current_user: OperationsDep
) -> PromotionResponse:
    promotion = session.scalar(
        select(Promotion).where(Promotion.id == promotion_id).with_for_update()
    )
    if promotion is None:
        raise operations_not_found("We could not find that promotion.")
    before = promotion_snapshot(promotion)
    promotion.is_active = False
    record_audit_event(
        session,
        current_user,
        entity_type="promotion",
        entity_id=promotion.id,
        action="deactivated",
        before_snapshot=before,
        after_snapshot=promotion_snapshot(promotion),
    )
    session.commit()
    return serialize_promotion(promotion)


@router.get("/settings", response_model=list[RestaurantSettingsResponse])
def list_restaurant_settings(
    session: SessionDep, _: OperationsDep
) -> list[RestaurantSettingsResponse]:
    locations = session.scalars(
        select(Location).options(selectinload(Location.hours)).order_by(Location.name)
    ).all()
    return [serialize_settings(location) for location in locations]


@router.put("/settings/{location_id}", response_model=RestaurantSettingsResponse)
def update_restaurant_settings(
    location_id: UUID,
    request: RestaurantSettingsUpdateRequest,
    session: SessionDep,
    current_user: OperationsDep,
) -> RestaurantSettingsResponse:
    location = session.scalar(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.hours))
        .with_for_update()
    )
    if location is None:
        raise operations_not_found("We could not find that restaurant location.")
    before = settings_snapshot(location)
    values = request.model_dump(exclude={"hours"})
    for field, value in values.items():
        setattr(location, field, value)
    existing_hours = {hour.weekday: hour for hour in location.hours}
    for item in request.hours:
        hour = existing_hours.pop(item.weekday, None)
        if hour is None:
            hour = OperatingHour(location_id=location.id, weekday=item.weekday)
            session.add(hour)
        hour.opens_at = item.opens_at
        hour.closes_at = item.closes_at
        hour.is_closed = item.is_closed
    for stale_hour in existing_hours.values():
        session.delete(stale_hour)
    session.flush()
    record_audit_event(
        session,
        current_user,
        entity_type="restaurant_settings",
        entity_id=location.id,
        action="updated",
        before_snapshot=before,
        after_snapshot=settings_snapshot(location),
    )
    session.commit()
    return serialize_settings(location)


@router.get("/customers", response_model=list[AdminCustomerResponse])
def list_customers(
    session: SessionDep,
    _: OperationsDep,
    query: Annotated[str | None, Query(max_length=100)] = None,
) -> list[AdminCustomerResponse]:
    statement = customer_statement().order_by(User.created_at.desc()).limit(100)
    if query and query.strip():
        phrase = f"%{query.strip()}%"
        statement = statement.where(
            User.display_name.ilike(phrase) | User.email.ilike(phrase)
        )
    return [
        serialize_customer(session, customer, include_orders=False)
        for customer in session.scalars(statement).all()
    ]


@router.get("/customers/{customer_id}", response_model=AdminCustomerResponse)
def read_customer(
    customer_id: UUID, session: SessionDep, _: OperationsDep
) -> AdminCustomerResponse:
    customer = session.scalar(customer_statement().where(User.id == customer_id))
    if customer is None:
        raise operations_not_found("We could not find that customer account.")
    return serialize_customer(session, customer, include_orders=True)


@router.patch("/customers/{customer_id}/state", response_model=AdminCustomerResponse)
def update_customer_account_state(
    customer_id: UUID,
    request: CustomerAccountStateRequest,
    session: SessionDep,
    current_user: OwnerDep,
) -> AdminCustomerResponse:
    customer = session.scalar(
        customer_statement().where(User.id == customer_id).with_for_update()
    )
    if customer is None:
        raise operations_not_found("We could not find that customer account.")
    before = customer_snapshot(customer)
    customer.is_active = request.is_active
    record_audit_event(
        session,
        current_user,
        entity_type="customer_account",
        entity_id=customer.id,
        action="activated" if request.is_active else "deactivated",
        before_snapshot=before,
        after_snapshot=customer_snapshot(customer),
    )
    session.commit()
    return serialize_customer(session, customer, include_orders=True)


@router.get("/reports", response_model=AdminReportResponse)
def read_reports(
    session: SessionDep,
    _: OperationsDep,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> AdminReportResponse:
    if starts_at is not None and starts_at.tzinfo is None:
        raise HTTPException(
            status_code=422, detail="Report start time must include a timezone."
        )
    if ends_at is not None and ends_at.tzinfo is None:
        raise HTTPException(
            status_code=422, detail="Report end time must include a timezone."
        )
    if starts_at is not None and ends_at is not None and ends_at <= starts_at:
        raise HTTPException(
            status_code=422, detail="Report end time must be after its start time."
        )
    order_statement = select(Order)
    if starts_at is not None:
        order_statement = order_statement.where(Order.created_at >= starts_at)
    if ends_at is not None:
        order_statement = order_statement.where(Order.created_at < ends_at)
    orders = session.scalars(order_statement).all()
    revenue_orders = [
        order
        for order in orders
        if OrderStatus(order.status) not in REVENUE_EXCLUDED_STATUSES
    ]
    revenue = sum(order.total_minor for order in revenue_orders)
    food_quantities: dict[tuple[str, int], list[int]] = {}
    if revenue_orders:
        revenue_ids = [order.id for order in revenue_orders]
        for item in session.scalars(
            select(OrderItem).where(OrderItem.order_id.in_(revenue_ids))
        ).all():
            key = (item.menu_item_name, item.unit_price_minor)
            quantity, amount = food_quantities.get(key, [0, 0])
            food_quantities[key] = [
                quantity + item.quantity,
                amount + item.line_total_minor,
            ]
    statuses: dict[OrderStatus, int] = {}
    for order in orders:
        current = OrderStatus(order.status)
        statuses[current] = statuses.get(current, 0) + 1
    promotion_uses: dict[str, list[int]] = {}
    for order in orders:
        if order.promotion_id is None:
            continue
        code = str(order.promotion_snapshot.get("code", "Archived promotion"))
        uses, discount = promotion_uses.get(code, [0, 0])
        promotion_uses[code] = [uses + 1, discount + order.promotion_discount_minor]
    review_statement = select(Review.status, func.count(Review.id))
    if starts_at is not None:
        review_statement = review_statement.where(Review.created_at >= starts_at)
    if ends_at is not None:
        review_statement = review_statement.where(Review.created_at < ends_at)
    review_rows = session.execute(review_statement.group_by(Review.status)).all()
    return AdminReportResponse(
        starts_at=starts_at,
        ends_at=ends_at,
        order_count=len(orders),
        revenue_order_count=len(revenue_orders),
        demo_revenue_minor=revenue,
        average_order_value_minor=revenue // len(revenue_orders)
        if revenue_orders
        else 0,
        popular_food=[
            ReportPopularFood(
                menu_item_name=name, quantity=values[0], revenue_minor=values[1]
            )
            for (name, _), values in sorted(
                food_quantities.items(),
                key=lambda entry: (-entry[1][0], entry[0][0]),
            )[:10]
        ],
        status_distribution=[
            ReportStatusDistribution(status=current, count=count)
            for current, count in sorted(
                statuses.items(), key=lambda entry: entry[0].value
            )
        ],
        promotion_use=[
            ReportPromotionUse(code=code, uses=values[0], discount_minor=values[1])
            for code, values in sorted(
                promotion_uses.items(), key=lambda entry: (-entry[1][0], entry[0])
            )
        ],
        review_moderation=[
            ReportReviewModeration(status=ReviewStatus(current), count=count)
            for current, count in sorted(review_rows, key=lambda entry: str(entry[0]))
        ],
    )


@router.get("/audit", response_model=list[AuditLogResponse])
def list_audit_events(
    session: SessionDep,
    _: OwnerDep,
    entity_type: Annotated[str | None, Query(max_length=48)] = None,
) -> list[AuditLogResponse]:
    statement = (
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    if entity_type and entity_type.strip():
        statement = statement.where(AuditLog.entity_type == entity_type.strip())
    return [serialize_audit(event) for event in session.scalars(statement).all()]
