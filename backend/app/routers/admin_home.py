from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionDep
from app.models import (
    HomeContent,
    HomeContentRevision,
    HomeContentRevisionAction,
    MediaAsset,
    PublicationState,
    RoleCode,
    User,
)
from app.routers.catalog import serialize_media
from app.schemas.admin import (
    AdminHomeContentResponse,
    HomeContentDraftRequest,
    HomeContentDraftSnapshot,
    HomeContentPublishRequest,
    HomeContentRevisionResponse,
)
from app.services.auth import require_roles

router = APIRouter(prefix="/api/v1/admin/home", tags=["Admin home"])
HomeEditorDep = Annotated[
    User, Depends(require_roles(RoleCode.OWNER, RoleCode.MANAGER))
]


def snapshot_from_request(
    request: HomeContentDraftRequest, content: HomeContent
) -> dict[str, str | None]:
    return {
        "heading": request.heading,
        "supporting_copy": request.supporting_copy,
        "action_label": request.action_label,
        "action_href": request.action_href,
        "media_id": str(request.media_id) if request.media_id is not None else None,
        "menu_item_id": str(content.menu_item_id)
        if content.menu_item_id is not None
        else None,
    }


def revision_response(revision: HomeContentRevision) -> HomeContentRevisionResponse:
    return HomeContentRevisionResponse(
        id=revision.id,
        action=HomeContentRevisionAction(revision.action),
        actor_name=revision.actor.display_name,
        created_at=revision.created_at,
        heading=str(revision.snapshot["heading"]),
        media_id=revision.media_id,
        snapshot=HomeContentDraftSnapshot.model_validate(revision.snapshot),
    )


def serialize_home_content(content: HomeContent) -> AdminHomeContentResponse:
    history = sorted(
        content.revisions, key=lambda revision: revision.created_at, reverse=True
    )
    latest_draft = (
        history[0]
        if history and history[0].action == HomeContentRevisionAction.DRAFT_SAVED
        else None
    )
    return AdminHomeContentResponse(
        id=content.id,
        content_key=content.content_key,
        heading=content.heading,
        supporting_copy=content.supporting_copy,
        action_label=content.action_label,
        action_href=content.action_href,
        display_order=content.display_order,
        publication_state=PublicationState(content.publication_state),
        media=serialize_media(content.media),
        latest_draft=revision_response(latest_draft) if latest_draft else None,
        history=[revision_response(revision) for revision in history[:5]],
    )


def select_home_content(content_key: str, session: SessionDep) -> HomeContent:
    content = session.scalar(
        select(HomeContent)
        .where(HomeContent.content_key == content_key)
        .options(
            joinedload(HomeContent.media),
            selectinload(HomeContent.revisions).joinedload(HomeContentRevision.actor),
        )
    )
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="We could not find that home section.",
        )
    return content


@router.get("", summary="List editable home-page sections")
def list_home_content(
    session: SessionDep, _: HomeEditorDep
) -> list[AdminHomeContentResponse]:
    content_blocks = session.scalars(
        select(HomeContent)
        .options(
            joinedload(HomeContent.media),
            selectinload(HomeContent.revisions).joinedload(HomeContentRevision.actor),
        )
        .order_by(HomeContent.display_order)
    ).all()
    return [serialize_home_content(content) for content in content_blocks]


@router.put("/{content_key}/draft", summary="Save a private home-page draft")
def save_home_draft(
    content_key: str,
    request: HomeContentDraftRequest,
    session: SessionDep,
    current_user: HomeEditorDep,
) -> AdminHomeContentResponse:
    content = select_home_content(content_key, session)
    if (
        request.media_id is not None
        and session.get(MediaAsset, request.media_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose an existing media asset for this home section.",
        )

    revision = HomeContentRevision(
        home_content_id=content.id,
        actor_id=current_user.id,
        media_id=request.media_id,
        action=HomeContentRevisionAction.DRAFT_SAVED,
        snapshot=snapshot_from_request(request, content),
    )
    session.add(revision)
    session.commit()
    session.expire_all()
    return serialize_home_content(select_home_content(content_key, session))


@router.post("/{content_key}/publish", summary="Publish a saved home-page draft")
def publish_home_draft(
    content_key: str,
    request: HomeContentPublishRequest,
    session: SessionDep,
    current_user: HomeEditorDep,
) -> AdminHomeContentResponse:
    content = select_home_content(content_key, session)
    revision = session.get(HomeContentRevision, request.revision_id)
    if revision is None or revision.home_content_id != content.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Choose a saved draft for this home section before publishing.",
        )
    if revision.action != HomeContentRevisionAction.DRAFT_SAVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This draft has already been published.",
        )

    snapshot = revision.snapshot
    media = session.get(MediaAsset, revision.media_id) if revision.media_id else None
    if revision.media_id is not None and media is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected media is no longer available.",
        )

    content.heading = str(snapshot["heading"])
    content.supporting_copy = str(snapshot["supporting_copy"])
    content.action_label = snapshot["action_label"]
    content.action_href = snapshot["action_href"]
    content.media_id = revision.media_id
    content.publication_state = PublicationState.PUBLISHED
    if media is not None:
        media.publication_state = PublicationState.PUBLISHED

    session.add(
        HomeContentRevision(
            home_content_id=content.id,
            actor_id=current_user.id,
            media_id=revision.media_id,
            action=HomeContentRevisionAction.PUBLISHED,
            snapshot=snapshot,
        )
    )
    session.commit()
    session.expire_all()
    return serialize_home_content(select_home_content(content_key, session))
