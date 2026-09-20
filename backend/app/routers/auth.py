from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import Settings, get_settings
from app.db.session import SessionDep
from app.models import RoleCode, User
from app.schemas.auth import (
    AdminSignInRequest,
    CurrentUserResponse,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.services.auth import (
    CurrentUserDep,
    create_token_pair,
    get_user_from_token,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def serialize_current_user(user: User) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=RoleCode(user.role.code),
    )


@router.post("/admin/sign-in", summary="Sign in as a local administrator")
def sign_in_admin(
    credentials: AdminSignInRequest,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    user = session.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.email == str(credentials.email).lower())
    )
    if (
        user is None
        or not user.is_active
        or RoleCode(user.role.code) != RoleCode.ADMIN
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = create_token_pair(user, settings)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", summary="Refresh a local access token")
def refresh_access_token(
    request: RefreshTokenRequest,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    user = get_user_from_token(request.refresh_token, "refresh", session, settings)
    access_token, refresh_token = create_token_pair(user, settings)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", summary="Read the authenticated local user")
def read_current_user(current_user: CurrentUserDep) -> CurrentUserResponse:
    return serialize_current_user(current_user)
