from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.db.session import SessionDep
from app.models import (
    Order,
    OrderItem,
    OrderStatus,
    Review,
    ReviewStatus,
    RoleCode,
    User,
)
from app.schemas.reviews import (
    AdminReviewResponse,
    CustomerReviewResponse,
    CustomerReviewUpdateRequest,
    CustomerReviewWriteRequest,
    PublicReviewListResponse,
    PublicReviewResponse,
    ReviewModerationAction,
    ReviewModerationRequest,
)
from app.services.auth import CustomerCurrentUserDep, require_roles

customer_router = APIRouter(prefix="/api/v1/account/reviews", tags=["Customer reviews"])
admin_router = APIRouter(
    prefix="/api/v1/admin/reviews", tags=["Admin review moderation"]
)
public_router = APIRouter(prefix="/api/v1/catalog/menu-items", tags=["Catalog"])
ReviewModeratorDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]


def account_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="We could not find that review in your account.",
    )


def serialize_customer_review(review: Review) -> CustomerReviewResponse:
    return CustomerReviewResponse(
        id=review.id,
        order_item_id=review.order_item_id,
        menu_item_slug=review.menu_item_slug,
        menu_item_name=review.menu_item_name,
        rating=review.rating,
        body=review.body,
        status=ReviewStatus(review.status),
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def reviewer_name(name: str) -> str:
    parts = [part for part in name.split() if part]
    if not parts:
        return "Nosh customer"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


@customer_router.get("", response_model=list[CustomerReviewResponse])
def list_customer_reviews(
    session: SessionDep, current_user: CustomerCurrentUserDep
) -> list[CustomerReviewResponse]:
    reviews = session.scalars(
        select(Review)
        .where(Review.customer_id == current_user.id)
        .order_by(Review.created_at.desc())
    ).all()
    return [serialize_customer_review(review) for review in reviews]


@customer_router.post(
    "", response_model=CustomerReviewResponse, status_code=status.HTTP_201_CREATED
)
def create_customer_review(
    request: CustomerReviewWriteRequest,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerReviewResponse:
    item = session.scalar(
        select(OrderItem)
        .join(OrderItem.order)
        .where(
            OrderItem.id == request.order_item_id,
            Order.customer_id == current_user.id,
            Order.status == OrderStatus.DELIVERED,
        )
    )
    if item is None:
        raise account_not_found()
    if (
        session.scalar(select(Review.id).where(Review.order_item_id == item.id))
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this ordered item.",
        )
    review = Review(
        customer_id=current_user.id,
        order_item_id=item.id,
        menu_item_id=item.menu_item_id,
        menu_item_slug=item.menu_item_slug,
        menu_item_name=item.menu_item_name,
        rating=request.rating,
        body=request.body,
        status=ReviewStatus.PENDING,
    )
    session.add(review)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this ordered item.",
        ) from None
    return serialize_customer_review(review)


@customer_router.patch("/{review_id}", response_model=CustomerReviewResponse)
def update_customer_review(
    review_id: UUID,
    request: CustomerReviewUpdateRequest,
    session: SessionDep,
    current_user: CustomerCurrentUserDep,
) -> CustomerReviewResponse:
    review = session.scalar(
        select(Review).where(
            Review.id == review_id, Review.customer_id == current_user.id
        )
    )
    if review is None:
        raise account_not_found()
    review.rating = request.rating
    review.body = request.body
    review.status = ReviewStatus.PENDING
    review.internal_reason = None
    review.moderated_by_id = None
    review.moderated_at = None
    session.commit()
    return serialize_customer_review(review)


@customer_router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_review(
    review_id: UUID, session: SessionDep, current_user: CustomerCurrentUserDep
) -> Response:
    review = session.scalar(
        select(Review).where(
            Review.id == review_id, Review.customer_id == current_user.id
        )
    )
    if review is None:
        raise account_not_found()
    session.delete(review)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{slug}/reviews", response_model=PublicReviewListResponse)
def list_public_reviews(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9-]+$")],
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> PublicReviewListResponse:
    reviews = session.scalars(
        select(Review)
        .options(joinedload(Review.customer))
        .where(Review.menu_item_slug == slug, Review.status == ReviewStatus.APPROVED)
        .order_by(Review.created_at.desc())
        .limit(limit)
    ).all()
    average = session.scalar(
        select(func.avg(Review.rating)).where(
            Review.menu_item_slug == slug, Review.status == ReviewStatus.APPROVED
        )
    )
    return PublicReviewListResponse(
        review_count=len(reviews),
        average_rating=float(average) if average is not None else None,
        reviews=[
            PublicReviewResponse(
                rating=review.rating,
                body=review.body,
                reviewer_name=reviewer_name(review.customer.display_name),
                created_at=review.created_at,
            )
            for review in reviews
        ],
    )


def serialize_admin_review(review: Review) -> AdminReviewResponse:
    return AdminReviewResponse(
        **serialize_customer_review(review).model_dump(),
        customer_name=review.customer.display_name,
        customer_email=review.customer.email,
        internal_reason=review.internal_reason,
        moderated_by_name=review.moderated_by.display_name
        if review.moderated_by
        else None,
        moderated_at=review.moderated_at,
    )


@admin_router.get("", response_model=list[AdminReviewResponse])
def list_admin_reviews(
    session: SessionDep,
    _: ReviewModeratorDep,
    status_value: Annotated[ReviewStatus | None, Query(alias="status")] = None,
) -> list[AdminReviewResponse]:
    statement = (
        select(Review)
        .options(joinedload(Review.customer), joinedload(Review.moderated_by))
        .order_by(Review.created_at.desc())
        .limit(100)
    )
    if status_value is not None:
        statement = statement.where(Review.status == status_value)
    return [
        serialize_admin_review(review) for review in session.scalars(statement).all()
    ]


@admin_router.post("/{review_id}/moderation", response_model=AdminReviewResponse)
def moderate_review(
    review_id: UUID,
    request: ReviewModerationRequest,
    session: SessionDep,
    current_user: ReviewModeratorDep,
) -> AdminReviewResponse:
    review = session.scalar(
        select(Review)
        .where(Review.id == review_id)
        .options(joinedload(Review.customer), joinedload(Review.moderated_by))
    )
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that review.",
        )
    next_status = {
        ReviewModerationAction.APPROVE: ReviewStatus.APPROVED,
        ReviewModerationAction.REJECT: ReviewStatus.REJECTED,
        ReviewModerationAction.HIDE: ReviewStatus.HIDDEN,
        ReviewModerationAction.RESTORE: ReviewStatus.APPROVED,
    }[request.action]
    review.status = next_status
    review.internal_reason = (
        request.internal_reason
        if request.action
        in {ReviewModerationAction.REJECT, ReviewModerationAction.HIDE}
        else None
    )
    review.moderated_by_id = current_user.id
    review.moderated_by = current_user
    review.moderated_at = datetime.now(UTC)
    session.commit()
    return serialize_admin_review(review)
