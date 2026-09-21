"""Add menu controls, availability auditing, and safe ordering fields.

Revision ID: 20260921_02
Revises: 20260921_01
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_02"
down_revision: str | Sequence[str] | None = "20260921_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("menu_items") as batch_op:
        batch_op.add_column(
            sa.Column(
                "demo_discount_minor",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "display_order",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "discount_non_negative", "demo_discount_minor >= 0"
        )
        batch_op.create_check_constraint(
            "discount_lte_base_price", "demo_discount_minor <= base_price_minor"
        )
        batch_op.create_check_constraint(
            "display_order_non_negative", "display_order >= 0"
        )
        batch_op.create_index(
            "ix_menu_items_category_visibility_order",
            ["category_id", "publication_state", "display_order"],
        )

    with op.batch_alter_table("option_groups") as batch_op:
        batch_op.add_column(
            sa.Column(
                "kind",
                sa.String(length=16),
                server_default=sa.text("'choice'"),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "kind_allowed", "kind IN ('choice', 'extra', 'removal')"
        )

    op.create_table(
        "catalog_changes",
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
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('menu_item', 'category', 'collection', 'featured')",
            name="entity_type_allowed",
        ),
        sa.CheckConstraint(
            "action IN ('created', 'updated', 'availability_changed', "
            "'featured_placement_changed', 'visibility_changed')",
            name="action_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_catalog_changes_actor_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_catalog_changes"),
    )
    op.create_index("ix_catalog_changes_actor_id", "catalog_changes", ["actor_id"])
    op.create_index(
        "ix_catalog_changes_entity_type", "catalog_changes", ["entity_type"]
    )
    op.create_index("ix_catalog_changes_entity_id", "catalog_changes", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_catalog_changes_entity_id", table_name="catalog_changes")
    op.drop_index("ix_catalog_changes_entity_type", table_name="catalog_changes")
    op.drop_index("ix_catalog_changes_actor_id", table_name="catalog_changes")
    op.drop_table("catalog_changes")

    with op.batch_alter_table("option_groups") as batch_op:
        batch_op.drop_constraint("kind_allowed", type_="check")
        batch_op.drop_column("kind")

    with op.batch_alter_table("menu_items") as batch_op:
        batch_op.drop_index("ix_menu_items_category_visibility_order")
        batch_op.drop_constraint("display_order_non_negative", type_="check")
        batch_op.drop_constraint("discount_lte_base_price", type_="check")
        batch_op.drop_constraint("discount_non_negative", type_="check")
        batch_op.drop_column("display_order")
        batch_op.drop_column("demo_discount_minor")
