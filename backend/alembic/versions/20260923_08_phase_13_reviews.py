"""Add eligible customer reviews and moderation state.

Revision ID: 20260923_08
Revises: 20260923_07
Create Date: 2026-09-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_08"
down_revision: str | Sequence[str] | None = "20260923_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("menu_item_id", sa.Uuid(), nullable=False),
        sa.Column("menu_item_slug", sa.String(length=160), nullable=False),
        sa.Column("menu_item_name", sa.String(length=160), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("internal_reason", sa.String(length=500)),
        sa.Column("moderated_by_id", sa.Uuid()),
        sa.Column("moderated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'hidden')",
            name="ck_reviews_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            name="fk_reviews_customer_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["moderated_by_id"],
            ["users.id"],
            name="fk_reviews_moderated_by_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_item_id"],
            ["order_items.id"],
            name="fk_reviews_order_item_id_order_items",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.UniqueConstraint("order_item_id", name="uq_reviews_order_item_id"),
    )
    op.create_index("ix_reviews_customer_id", "reviews", ["customer_id"])
    op.create_index("ix_reviews_order_item_id", "reviews", ["order_item_id"])
    op.create_index("ix_reviews_menu_item_id", "reviews", ["menu_item_id"])
    op.create_index("ix_reviews_moderated_by_id", "reviews", ["moderated_by_id"])
    op.create_index("ix_reviews_status_created_at", "reviews", ["status", "created_at"])
    op.create_index(
        "ix_reviews_menu_status_created_at",
        "reviews",
        ["menu_item_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_menu_status_created_at", table_name="reviews")
    op.drop_index("ix_reviews_status_created_at", table_name="reviews")
    op.drop_index("ix_reviews_moderated_by_id", table_name="reviews")
    op.drop_index("ix_reviews_menu_item_id", table_name="reviews")
    op.drop_index("ix_reviews_order_item_id", table_name="reviews")
    op.drop_index("ix_reviews_customer_id", table_name="reviews")
    op.drop_table("reviews")
