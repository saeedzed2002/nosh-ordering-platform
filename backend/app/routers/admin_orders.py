from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.db.session import SessionDep
from app.models import RoleCode, User
from app.schemas.orders import OrderReceiptResponse, OrderStatusTransitionRequest
from app.services.auth import require_roles
from app.services.checkout import serialize_order
from app.services.order_lifecycle import transition_order_status

router = APIRouter(prefix="/api/v1/admin/orders", tags=["Admin order lifecycle"])
OrderLifecycleDep = Annotated[
    User,
    Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER, RoleCode.KITCHEN)),
]


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
    order = transition_order_status(session, public_reference, request, current_user)
    return serialize_order(order)
