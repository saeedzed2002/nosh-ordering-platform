from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status

from app.db.session import SessionDep
from app.schemas.orders import CheckoutRequest, OrderReceiptResponse
from app.services.auth import OptionalCustomerDep
from app.services.checkout import (
    create_order,
    order_by_public_reference,
    serialize_order,
)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post(
    "/checkout",
    response_model=OrderReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a durable local-demo order",
)
def checkout_customer_order(
    request: CheckoutRequest,
    response: Response,
    session: SessionDep,
    customer: OptionalCustomerDep,
) -> OrderReceiptResponse:
    order, replayed = create_order(session, request, customer)
    if replayed:
        response.status_code = status.HTTP_200_OK
    return serialize_order(order)


@router.get(
    "/{public_reference}",
    response_model=OrderReceiptResponse,
    summary="Read a public order receipt",
)
def read_customer_order(
    public_reference: Annotated[
        str,
        Path(pattern=r"^N-[0-9A-F]{16}$", description="Public Nosh order reference"),
    ],
    session: SessionDep,
) -> OrderReceiptResponse:
    order = order_by_public_reference(session, public_reference)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that order receipt.",
        )
    return serialize_order(order)
