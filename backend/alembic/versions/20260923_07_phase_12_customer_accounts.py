"""Add customer account ownership, addresses, and favorites.

Revision ID: 20260923_07
Revises: 20260921_06
Create Date: 2026-09-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260923_07"
down_revision: str | Sequence[str] | None = "20260921_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID = sa.Uuid()
TIMESTAMP = sa.DateTime(timezone=True)


def audit_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", UUID, nullable=False),
        sa.Column(
            "created_at",
            TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "customer_addresses",
        *audit_columns(),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False),
        sa.Column("address_text", sa.Text(), nullable=False),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_customer_addresses_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_addresses"),
        sa.UniqueConstraint(
            "user_id", "label", name="uq_customer_addresses_customer_address_label"
        ),
    )
    op.create_index("ix_customer_addresses_user_id", "customer_addresses", ["user_id"])
    op.create_index(
        "uq_customer_addresses_default_per_user",
        "customer_addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
        sqlite_where=sa.text("is_default"),
    )
    op.create_table(
        "customer_favorites",
        *audit_columns(),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_customer_favorites_menu_item_id_menu_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_customer_favorites_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_customer_favorites"),
        sa.UniqueConstraint(
            "user_id",
            "menu_item_id",
            name="uq_customer_favorites_customer_favorite_item",
        ),
    )
    op.create_index("ix_customer_favorites_user_id", "customer_favorites", ["user_id"])
    op.create_index(
        "ix_customer_favorites_menu_item_id", "customer_favorites", ["menu_item_id"]
    )
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("customer_id", UUID))
        batch_op.create_foreign_key(
            "fk_orders_customer_id_users",
            "users",
            ["customer_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index(
        "ix_orders_customer_created_at", "orders", ["customer_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_orders_customer_created_at", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("fk_orders_customer_id_users", type_="foreignkey")
        batch_op.drop_column("customer_id")
    op.drop_index("ix_customer_favorites_menu_item_id", table_name="customer_favorites")
    op.drop_index("ix_customer_favorites_user_id", table_name="customer_favorites")
    op.drop_table("customer_favorites")
    op.drop_index(
        "uq_customer_addresses_default_per_user", table_name="customer_addresses"
    )
    op.drop_index("ix_customer_addresses_user_id", table_name="customer_addresses")
    op.drop_table("customer_addresses")
