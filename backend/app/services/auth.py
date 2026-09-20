from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.db.session import SessionDep
from app.models import RoleCode, User

JWT_ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def require_jwt_secret(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured for this local environment.",
        )
    if len(settings.jwt_secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The local JWT secret must be at least 32 bytes.",
        )
    return settings.jwt_secret


def create_token(
    *,
    user: User,
    token_type: str,
    expires_in_minutes: int,
    settings: Settings,
) -> str:
    secret = require_jwt_secret(settings)
    if user.role is None:
        raise ValueError("A token cannot be created for a user without a role.")

    expires_at = datetime.now(UTC) + timedelta(minutes=expires_in_minutes)
    claims = {
        "sub": str(user.id),
        "role": RoleCode(user.role.code).value,
        "token_type": token_type,
        "exp": expires_at,
    }
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def create_token_pair(user: User, settings: Settings) -> tuple[str, str]:
    return (
        create_token(
            user=user,
            token_type="access",
            expires_in_minutes=settings.access_token_minutes,
            settings=settings,
        ),
        create_token(
            user=user,
            token_type="refresh",
            expires_in_minutes=settings.refresh_token_minutes,
            settings=settings,
        ),
    )


def decode_token(
    token: str, expected_token_type: str, settings: Settings
) -> dict[str, str]:
    secret = require_jwt_secret(settings)
    try:
        claims = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if claims.get("token_type") != expected_token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token type is not accepted here.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def get_user_from_token(
    token: str, expected_token_type: str, session: Session, settings: Settings
) -> User:
    claims = decode_token(token, expected_token_type, settings)
    try:
        user_id = UUID(claims["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication subject.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = session.scalar(
        select(User).options(joinedload(User.role)).where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are not active.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_user_from_token(credentials.credentials, "access", session, settings)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: RoleCode):
    def enforce_role(current_user: CurrentUserDep) -> User:
        if RoleCode(current_user.role.code) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role is not allowed to perform this action.",
            )
        return current_user

    return enforce_role
