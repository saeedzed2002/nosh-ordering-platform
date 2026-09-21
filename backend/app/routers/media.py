from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import Settings, get_settings
from app.db.session import SessionDep
from app.models import (
    HomeContent,
    HomeContentRevision,
    MediaAsset,
    PublicationState,
    RoleCode,
    User,
)
from app.schemas.media import (
    AdminMediaAssetResponse,
    MediaAssetUpdateRequest,
    MediaUsageResponse,
)
from app.services.auth import require_roles
from app.services.media import (
    MAX_IMAGE_BYTES,
    MediaValidationError,
    persist_image,
    regenerate_thumbnail,
    remove_stored_image,
    validate_image_payload,
)

router = APIRouter(prefix="/api/v1", tags=["Media"])
MediaManagerDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]


def serialize_media_asset(
    media: MediaAsset, usages: list[MediaUsageResponse] | None = None
) -> AdminMediaAssetResponse:
    return AdminMediaAssetResponse(
        id=media.id,
        original_filename=media.original_filename,
        mime_type=media.mime_type,
        byte_size=media.byte_size,
        width=media.width,
        height=media.height,
        checksum_sha256=media.checksum_sha256,
        alt_text=media.alt_text,
        focal_point_x=media.focal_point_x,
        focal_point_y=media.focal_point_y,
        source_description=media.source_description,
        credit=media.credit,
        publication_state=PublicationState(media.publication_state),
        usages=usages or [],
    )


def media_usages(session: SessionDep) -> dict[object, list[MediaUsageResponse]]:
    usages: dict[object, list[MediaUsageResponse]] = {}
    current_content = session.scalars(
        select(HomeContent).where(HomeContent.media_id.is_not(None))
    ).all()
    for content in current_content:
        usages.setdefault(content.media_id, []).append(
            MediaUsageResponse(
                content_key=content.content_key,
                label=f"Live {content.content_key.replace('-', ' ')}",
                state=PublicationState(content.publication_state).value,
            )
        )

    home_revisions = session.scalars(
        select(HomeContentRevision)
        .where(HomeContentRevision.media_id.is_not(None))
        .options(joinedload(HomeContentRevision.home_content))
    ).all()
    for revision in home_revisions:
        content_key = revision.home_content.content_key
        usages.setdefault(revision.media_id, []).append(
            MediaUsageResponse(
                content_key=content_key,
                label=f"Home revision: {content_key.replace('-', ' ')}",
                state=revision.action.value,
            )
        )
    return usages


def media_file_path(media_root: Path, relative_path: str) -> Path:
    root = media_root.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    return path


@router.get("/media/{media_id}/thumbnail", summary="Read a published media thumbnail")
def read_public_thumbnail(
    media_id: UUID,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    media = session.scalar(
        select(MediaAsset).where(
            MediaAsset.id == media_id,
            MediaAsset.publication_state == PublicationState.PUBLISHED,
        )
    )
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    thumbnail_path = media_file_path(settings.media_root, media.thumbnail_path)
    if not thumbnail_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    return FileResponse(thumbnail_path, media_type="image/webp")


@router.get("/admin/media", summary="List media metadata for an administrator")
def list_admin_media(
    session: SessionDep, _: MediaManagerDep
) -> list[AdminMediaAssetResponse]:
    media_assets = session.scalars(
        select(MediaAsset).order_by(MediaAsset.created_at.desc())
    ).all()
    usages = media_usages(session)
    return [
        serialize_media_asset(media, usages.get(media.id)) for media in media_assets
    ]


@router.get(
    "/admin/media/{media_id}/original",
    summary="Read an original media file as an administrator",
)
def read_original_media(
    media_id: UUID,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    _: MediaManagerDep,
) -> FileResponse:
    media = session.get(MediaAsset, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    original_path = media_file_path(settings.media_root, media.original_path)
    if not original_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    return FileResponse(
        original_path, media_type=media.mime_type, filename=media.original_filename
    )


@router.get(
    "/admin/media/{media_id}/thumbnail",
    summary="Read a media thumbnail as an administrator",
)
def read_admin_thumbnail(
    media_id: UUID,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    _: MediaManagerDep,
) -> FileResponse:
    media = session.get(MediaAsset, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    thumbnail_path = media_file_path(settings.media_root, media.thumbnail_path)
    if not thumbnail_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )
    return FileResponse(thumbnail_path, media_type="image/webp")


@router.post(
    "/admin/media", status_code=status.HTTP_201_CREATED, summary="Upload local media"
)
async def upload_media(
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    _: MediaManagerDep,
    file: Annotated[
        UploadFile, File(description="A JPEG, PNG, or WebP file up to 5 MB")
    ],
    alt_text: Annotated[str, Form(min_length=1, max_length=500)],
    focal_point_x: Annotated[int, Form(ge=0, le=100)] = 50,
    focal_point_y: Annotated[int, Form(ge=0, le=100)] = 50,
    source_description: Annotated[str | None, Form(max_length=500)] = None,
    credit: Annotated[str | None, Form(max_length=500)] = None,
) -> AdminMediaAssetResponse:
    try:
        payload = await file.read(MAX_IMAGE_BYTES + 1)
    finally:
        await file.close()

    try:
        validated_image = validate_image_payload(payload, file.content_type)
    except MediaValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None

    stored_image = persist_image(
        settings.media_root,
        file.filename or "upload",
        validated_image,
        focal_point_x=focal_point_x,
        focal_point_y=focal_point_y,
    )
    media = MediaAsset(
        id=stored_image.id,
        original_filename=file.filename or "upload",
        original_path=stored_image.original_path,
        thumbnail_path=stored_image.thumbnail_path,
        mime_type=validated_image.mime_type,
        byte_size=len(validated_image.payload),
        width=validated_image.width,
        height=validated_image.height,
        checksum_sha256=validated_image.checksum_sha256,
        alt_text=alt_text,
        focal_point_x=focal_point_x,
        focal_point_y=focal_point_y,
        source_description=source_description,
        credit=credit,
    )
    try:
        session.add(media)
        session.commit()
    except Exception:
        session.rollback()
        remove_stored_image(settings.media_root, stored_image)
        raise
    session.refresh(media)
    return serialize_media_asset(media)


@router.patch(
    "/admin/media/{media_id}",
    summary="Update administrator-managed media metadata",
)
def update_media(
    media_id: UUID,
    request: MediaAssetUpdateRequest,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
    _: MediaManagerDep,
) -> AdminMediaAssetResponse:
    media = session.get(MediaAsset, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media was not found."
        )

    changes = request.model_dump(exclude_unset=True)
    if not changes:
        return serialize_media_asset(media, media_usages(session).get(media.id))

    requested_state = changes.get("publication_state")
    if requested_state == PublicationState.DRAFT:
        is_live = session.scalar(
            select(HomeContent.id).where(
                HomeContent.media_id == media.id,
                HomeContent.publication_state == PublicationState.PUBLISHED,
            )
        )
        if is_live is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Replace this live home image before returning it to draft.",
            )

    next_focal_x = changes.get("focal_point_x", media.focal_point_x)
    next_focal_y = changes.get("focal_point_y", media.focal_point_y)
    if next_focal_x != media.focal_point_x or next_focal_y != media.focal_point_y:
        regenerate_thumbnail(
            settings.media_root,
            original_path=media.original_path,
            thumbnail_path=media.thumbnail_path,
            focal_point_x=next_focal_x,
            focal_point_y=next_focal_y,
        )

    for field_name, value in changes.items():
        setattr(media, field_name, value)
    session.commit()
    session.refresh(media)
    return serialize_media_asset(media, media_usages(session).get(media.id))
