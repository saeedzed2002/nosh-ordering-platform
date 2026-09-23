from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import ReviewStatus


class CustomerReviewWriteRequest(BaseModel):
    order_item_id: UUID
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=12, max_length=1500)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Review text cannot be blank.")
        return normalized


class CustomerReviewUpdateRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=12, max_length=1500)

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Review text cannot be blank.")
        return normalized


class CustomerReviewResponse(BaseModel):
    id: UUID
    order_item_id: UUID
    menu_item_slug: str
    menu_item_name: str
    rating: int
    body: str
    status: ReviewStatus
    created_at: datetime
    updated_at: datetime


class CustomerReviewEligibilityResponse(BaseModel):
    menu_item_slugs: list[str]


class PublicReviewResponse(BaseModel):
    rating: int
    body: str
    reviewer_name: str
    created_at: datetime


class PublicReviewListResponse(BaseModel):
    review_count: int
    average_rating: float | None
    reviews: list[PublicReviewResponse]


class ReviewModerationAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    HIDE = "hide"
    RESTORE = "restore"


class ReviewModerationRequest(BaseModel):
    action: ReviewModerationAction
    internal_reason: str | None = Field(default=None, max_length=500)

    @field_validator("internal_reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_sensitive_reason(self) -> "ReviewModerationRequest":
        if (
            self.action in {ReviewModerationAction.REJECT, ReviewModerationAction.HIDE}
            and self.internal_reason is None
        ):
            raise ValueError(
                "An internal reason is required when rejecting or hiding a review."
            )
        return self


class AdminReviewResponse(CustomerReviewResponse):
    customer_name: str
    customer_email: str
    internal_reason: str | None
    moderated_by_name: str | None
    moderated_at: datetime | None
