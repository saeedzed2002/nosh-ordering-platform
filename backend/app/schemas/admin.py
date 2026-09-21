from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import HomeContentRevisionAction, PublicationState
from app.schemas.catalog import MediaSummary


class HomeContentDraftRequest(BaseModel):
    heading: str = Field(min_length=1, max_length=240)
    supporting_copy: str = Field(min_length=1)
    action_label: str | None = Field(default=None, max_length=100)
    action_href: str | None = Field(default=None, max_length=255)
    media_id: UUID | None = None


class HomeContentPublishRequest(BaseModel):
    revision_id: UUID


class HomeContentDraftSnapshot(BaseModel):
    heading: str
    supporting_copy: str
    action_label: str | None
    action_href: str | None
    media_id: UUID | None


class HomeContentRevisionResponse(BaseModel):
    id: UUID
    action: HomeContentRevisionAction
    actor_name: str
    created_at: datetime
    heading: str
    media_id: UUID | None
    snapshot: HomeContentDraftSnapshot


class AdminHomeContentResponse(BaseModel):
    id: UUID
    content_key: str
    heading: str
    supporting_copy: str
    action_label: str | None
    action_href: str | None
    display_order: int
    publication_state: PublicationState
    media: MediaSummary | None
    latest_draft: HomeContentRevisionResponse | None
    history: list[HomeContentRevisionResponse]
