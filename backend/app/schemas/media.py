from uuid import UUID

from pydantic import BaseModel

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
