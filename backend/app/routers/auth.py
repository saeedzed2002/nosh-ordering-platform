from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.core.config import Settings, get_settings
from app.db.session import SessionDep
from app.models import Role, RoleCode, User
from app.schemas.auth import (
    AdminSignInRequest,
    CurrentUserResponse,
    CustomerSignInRequest,
    CustomerSignUpRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)
from app.services.auth import (
    CurrentUserDep,
    create_token_pair,
    get_user_from_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
STAFF_SIGN_IN_ROLES = frozenset({RoleCode.KITCHEN, RoleCode.MANAGER, RoleCode.OWNER})


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
        or RoleCode(user.role.code) not in STAFF_SIGN_IN_ROLES
        or not verify_password(credentials.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token = create_token_pair(user, settings)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


def customer_for_credentials(session: SessionDep, email: str, password: str) -> User:
    user = session.scalar(
        select(User).options(joinedload(User.role)).where(User.email == email.lower())
    )
    if (
        user is None
        or not user.is_active
        or RoleCode(user.role.code) != RoleCode.CUSTOMER
        or not verify_password(password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/customer/sign-up", summary="Create and sign in a customer account")
def sign_up_customer(
    request: CustomerSignUpRequest,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    customer_role = session.scalar(select(Role).where(Role.code == RoleCode.CUSTOMER))
    if customer_role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The customer role is not available in this local environment.",
        )
    user = User(
        email=str(request.email).lower(),
        display_name=request.display_name.strip(),
        password_hash=hash_password(request.password),
        role_id=customer_role.id,
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses this email address.",
        ) from None
    user.role = customer_role
    access_token, refresh_token = create_token_pair(user, settings)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/customer/sign-in", summary="Sign in as a customer")
def sign_in_customer(
    credentials: CustomerSignInRequest,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenPairResponse:
    user = customer_for_credentials(
        session, str(credentials.email), credentials.password
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
