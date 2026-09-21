from uuid import UUID

from pydantic import BaseModel, Field

from app.models import PublicationState


class MediaAssetResponse(BaseModel):
    id: UUID
    original_filename: str
    mime_type: str
    byte_size: int
    width: int
    height: int
    checksum_sha256: str
    alt_text: str
    focal_point_x: int
    focal_point_y: int
    source_description: str | None
    credit: str | None
    publication_state: PublicationState


class MediaUsageResponse(BaseModel):
    content_key: str
    label: str
    state: str


class AdminMediaAssetResponse(MediaAssetResponse):
    usages: list[MediaUsageResponse] = Field(default_factory=list)


class MediaAssetUpdateRequest(BaseModel):
    alt_text: str | None = Field(default=None, min_length=1, max_length=500)
    focal_point_x: int | None = Field(default=None, ge=0, le=100)
    focal_point_y: int | None = Field(default=None, ge=0, le=100)
    source_description: str | None = Field(default=None, max_length=500)
    credit: str | None = Field(default=None, max_length=500)
    publication_state: PublicationState | None = None
