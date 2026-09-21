"""Add customer-safe restaurant contact data for order tracking.

Revision ID: 20260921_05
Revises: 20260921_04
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_05"
down_revision: str | Sequence[str] | None = "20260921_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "locations",
        sa.Column(
            "contact_phone",
            sa.String(length=30),
            server_default=sa.text("'+1 (555) 010-0195'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("locations", "contact_phone")
