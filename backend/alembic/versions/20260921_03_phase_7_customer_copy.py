"""Refresh the seeded featured-dish copy after customer-menu delivery.

Revision ID: 20260921_03
Revises: 20260921_02
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_03"
down_revision: str | Sequence[str] | None = "20260921_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

old_copy = "A featured local-demo dish, ready for the later menu API."
new_copy = (
    "A featured dish with its full ingredients, availability, and notes ready "
    "to explore."
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE home_content "
            "SET supporting_copy = :new_copy "
            "WHERE content_key = 'featured-dish' "
            "AND supporting_copy = :old_copy"
        ).bindparams(new_copy=new_copy, old_copy=old_copy)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE home_content "
            "SET supporting_copy = :old_copy "
            "WHERE content_key = 'featured-dish' "
            "AND supporting_copy = :new_copy"
        ).bindparams(new_copy=new_copy, old_copy=old_copy)
    )
