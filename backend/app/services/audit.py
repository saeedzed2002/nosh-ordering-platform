from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def record_audit_event(
    session: Session,
    actor: User,
    *,
    entity_type: str,
    entity_id: UUID | None,
    action: str,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
) -> None:
    """Stage a safe, inspectable audit record in the caller's transaction."""

    session.add(
        AuditLog(
            actor_id=actor.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )
    )
