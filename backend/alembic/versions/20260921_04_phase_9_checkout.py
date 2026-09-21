"""Add durable checkout, promotion, and immutable order snapshots.

Revision ID: 20260921_04
Revises: 20260921_03
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_04"
down_revision: str | Sequence[str] | None = "20260921_03"
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
        "promotions",
        *audit_columns(),
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column(
            "minimum_order_minor",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("starts_at", TIMESTAMP),
        sa.Column("ends_at", TIMESTAMP),
        sa.Column("usage_limit", sa.Integer()),
        sa.Column(
            "usage_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("code = upper(code)", name="ck_promotions_code_upper"),
        sa.CheckConstraint(
            "kind IN ('fixed_amount', 'percentage')",
            name="ck_promotions_kind_allowed",
        ),
        sa.CheckConstraint(
            "discount_value > 0", name="ck_promotions_discount_value_positive"
        ),
        sa.CheckConstraint(
            "minimum_order_minor >= 0",
            name="ck_promotions_minimum_order_non_negative",
        ),
        sa.CheckConstraint(
            "usage_count >= 0", name="ck_promotions_usage_count_non_negative"
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_promotions_usage_limit_positive",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="ck_promotions_valid_window",
        ),
        sa.CheckConstraint(
            "(kind = 'fixed_amount' AND discount_value >= 1) "
            "OR (kind = 'percentage' AND discount_value BETWEEN 1 AND 10000)",
            name="ck_promotions_discount_value_valid_for_kind",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_promotions"),
        sa.UniqueConstraint("code", name="uq_promotions_code"),
    )

    op.create_table(
        "orders",
        *audit_columns(),
        sa.Column("public_reference", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("location_id", UUID, nullable=False),
        sa.Column("promotion_id", UUID),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fulfillment_method", sa.String(length=16), nullable=False),
        sa.Column("scheduled_for", TIMESTAMP),
        sa.Column("recipient_snapshot", sa.JSON(), nullable=False),
        sa.Column("fulfillment_snapshot", sa.JSON(), nullable=False),
        sa.Column("promotion_snapshot", sa.JSON(), nullable=False),
        sa.Column("payment_snapshot", sa.JSON(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("subtotal_minor", sa.Integer(), nullable=False),
        sa.Column("promotion_discount_minor", sa.Integer(), nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "public_reference = upper(public_reference)",
            name="ck_orders_reference_upper",
        ),
        sa.CheckConstraint(
            "fulfillment_method IN ('pickup', 'delivery')",
            name="ck_orders_fulfillment_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'submitted', 'accepted', 'preparing', "
            "'ready_for_pickup', 'ready_for_courier', 'handed_to_customer', "
            "'handed_to_courier', 'out_for_delivery', 'delivered', 'declined', "
            "'cancelled', 'needs_contact')",
            name="ck_orders_status_allowed",
        ),
        sa.CheckConstraint(
            "subtotal_minor >= 0", name="ck_orders_subtotal_non_negative"
        ),
        sa.CheckConstraint(
            "promotion_discount_minor >= 0",
            name="ck_orders_promotion_discount_non_negative",
        ),
        sa.CheckConstraint(
            "promotion_discount_minor <= subtotal_minor",
            name="ck_orders_promotion_discount_lte_subtotal",
        ),
        sa.CheckConstraint(
            "total_minor = subtotal_minor - promotion_discount_minor",
            name="ck_orders_total_matches_components",
        ),
        sa.CheckConstraint(
            "length(currency_code) = 3 AND currency_code = upper(currency_code)",
            name="ck_orders_currency_code_uppercase",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.id"], name="fk_orders_location_id_locations"
        ),
        sa.ForeignKeyConstraint(
            ["promotion_id"],
            ["promotions.id"],
            name="fk_orders_promotion_id_promotions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_orders"),
        sa.UniqueConstraint("public_reference", name="uq_orders_public_reference"),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
    )
    op.create_index("ix_orders_location_id", "orders", ["location_id"])
    op.create_index("ix_orders_promotion_id", "orders", ["promotion_id"])

    op.create_table(
        "order_items",
        *audit_columns(),
        sa.Column("order_id", UUID, nullable=False),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.Column("menu_item_slug", sa.String(length=160), nullable=False),
        sa.Column("menu_item_name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500)),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("line_total_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("item_snapshot", sa.JSON(), nullable=False),
        sa.Column("selected_options_snapshot", sa.JSON(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint(
            "unit_price_minor >= 0", name="ck_order_items_unit_price_non_negative"
        ),
        sa.CheckConstraint(
            "line_total_minor >= 0", name="ck_order_items_line_total_non_negative"
        ),
        sa.CheckConstraint(
            "line_total_minor = unit_price_minor * quantity",
            name="ck_order_items_line_total_matches",
        ),
        sa.CheckConstraint(
            "length(currency_code) = 3 AND currency_code = upper(currency_code)",
            name="ck_order_items_currency_code_uppercase",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"], name="fk_order_items_order_id_orders"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_items"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_menu_item_id", "order_items", ["menu_item_id"])

    op.create_table(
        "order_status_events",
        *audit_columns(),
        sa.Column("order_id", UUID, nullable=False),
        sa.Column("actor_id", UUID),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.CheckConstraint(
            "status IN ('scheduled', 'submitted', 'accepted', 'preparing', "
            "'ready_for_pickup', 'ready_for_courier', 'handed_to_customer', "
            "'handed_to_courier', 'out_for_delivery', 'delivered', 'declined', "
            "'cancelled', 'needs_contact')",
            name="ck_order_status_events_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_order_status_events_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name="fk_order_status_events_order_id_orders",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_order_status_events"),
    )
    op.create_index(
        "ix_order_status_events_order_id", "order_status_events", ["order_id"]
    )
    op.create_index(
        "ix_order_status_events_actor_id", "order_status_events", ["actor_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_order_status_events_actor_id", table_name="order_status_events")
    op.drop_index("ix_order_status_events_order_id", table_name="order_status_events")
    op.drop_table("order_status_events")

    op.drop_index("ix_order_items_menu_item_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders_promotion_id", table_name="orders")
    op.drop_index("ix_orders_location_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("promotions")
