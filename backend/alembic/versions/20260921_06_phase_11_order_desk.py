"""Add location ordering controls and order-desk lookup indexes.

Revision ID: 20260921_06
Revises: 20260921_05
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_06"
down_revision: str | Sequence[str] | None = "20260921_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("locations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "online_ordering_state",
                sa.String(length=16),
                server_default=sa.text("'on'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("online_ordering_paused_until", sa.DateTime(timezone=True))
        )
        batch_op.create_check_constraint(
            "ck_locations_online_ordering_state_allowed",
            "online_ordering_state IN ('on', 'timed_pause', 'off')",
        )
        batch_op.create_check_constraint(
            "ck_locations_online_ordering_pause_window",
            "(online_ordering_state = 'timed_pause' "
            "AND online_ordering_paused_until IS NOT NULL) "
            "OR (online_ordering_state != 'timed_pause' "
            "AND online_ordering_paused_until IS NULL)",
        )
    op.create_index("ix_orders_status_created_at", "orders", ["status", "created_at"])
    op.create_index(
        "ix_orders_location_created_at", "orders", ["location_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_orders_location_created_at", table_name="orders")
    op.drop_index("ix_orders_status_created_at", table_name="orders")
    with op.batch_alter_table("locations") as batch_op:
        batch_op.drop_constraint("ck_locations_online_ordering_pause_window")
        batch_op.drop_constraint("ck_locations_online_ordering_state_allowed")
        batch_op.drop_column("online_ordering_paused_until")
        batch_op.drop_column("online_ordering_state")
