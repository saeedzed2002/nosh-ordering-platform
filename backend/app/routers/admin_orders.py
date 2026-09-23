from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.db.session import SessionDep
from app.models import FulfillmentMethod, OrderStatus, RoleCode, User
from app.schemas.admin_orders import (
    AdminOrderDetailResponse,
    AdminOrderListResponse,
    LocationOrderControlsRequest,
    LocationOrderControlsResponse,
    OrderDeskQueue,
)
from app.schemas.orders import OrderReceiptResponse, OrderStatusTransitionRequest
from app.services.auth import require_roles
from app.services.checkout import serialize_order
from app.services.order_desk import (
    all_location_controls,
    list_orders,
    location_references,
    order_detail,
    serialize_order_list_item,
    update_location_controls,
)
from app.services.order_lifecycle import transition_order_status

router = APIRouter(prefix="/api/v1/admin/orders", tags=["Admin order lifecycle"])
OrderLifecycleDep = Annotated[
    User,
    Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER, RoleCode.KITCHEN)),
]
OrderControlsDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]


@router.get(
    "", response_model=AdminOrderListResponse, summary="List daily order queues"
)
def list_order_desk(
    session: SessionDep,
    _: OrderLifecycleDep,
    query: Annotated[str | None, Query(max_length=100)] = None,
    queue: OrderDeskQueue | None = None,
    status_value: Annotated[OrderStatus | None, Query(alias="status")] = None,
    location_id: UUID | None = None,
    fulfillment_method: FulfillmentMethod | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> AdminOrderListResponse:
    orders, queue_counts = list_orders(
        session,
        query=query,
        queue=queue,
        status_value=status_value,
        location_id=location_id,
        fulfillment_method=fulfillment_method,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    return AdminOrderListResponse(
        orders=[serialize_order_list_item(order) for order in orders],
        queue_counts=queue_counts,
        locations=location_references(session),
        total=len(orders),
    )


@router.get(
    "/controls",
    response_model=list[LocationOrderControlsResponse],
    summary="Read online-order controls for each kitchen location",
)
def read_order_controls(
    session: SessionDep, _: OrderControlsDep
) -> list[LocationOrderControlsResponse]:
    return all_location_controls(session)


@router.put(
    "/locations/{location_id}/controls",
    response_model=LocationOrderControlsResponse,
    summary="Update online-order availability and kitchen limits",
)
def save_order_controls(
    location_id: UUID,
    request: LocationOrderControlsRequest,
    session: SessionDep,
    current_user: OrderControlsDep,
) -> LocationOrderControlsResponse:
    return update_location_controls(session, location_id, request, current_user)


@router.get(
    "/{public_reference}",
    response_model=AdminOrderDetailResponse,
    summary="Read an internal order detail",
)
def read_order_detail(
    public_reference: Annotated[
        str,
        Path(pattern=r"^N-[0-9A-F]{16}$", description="Public Nosh order reference"),
    ],
    session: SessionDep,
    _: OrderLifecycleDep,
) -> AdminOrderDetailResponse:
    return order_detail(session, public_reference)


@router.post(
    "/{public_reference}/transitions",
    response_model=OrderReceiptResponse,
    summary="Record a valid staff order-status transition",
)
def transition_order(
    public_reference: Annotated[
        str,
        Path(pattern=r"^N-[0-9A-F]{16}$", description="Public Nosh order reference"),
    ],
    request: OrderStatusTransitionRequest,
    session: SessionDep,
    current_user: OrderLifecycleDep,
) -> OrderReceiptResponse:
    if request.status in {OrderStatus.DECLINED, OrderStatus.CANCELLED} and (
        RoleCode(current_user.role.code) == RoleCode.KITCHEN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A manager or owner must decline or cancel an order.",
        )
    order = transition_order_status(session, public_reference, request, current_user)
    return serialize_order(order)
