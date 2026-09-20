"""Harden Phase 4 roles, integrity rules, and foreign-key access paths.

Revision ID: 20260920_02
Revises: 20260920_01
Create Date: 2026-09-20 00:00:00
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_02"
down_revision: str | Sequence[str] | None = "20260920_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KITCHEN_ROLE_ID = uuid5(NAMESPACE_URL, "https://nosh.local/phase-4/role:kitchen")


CHECK_CONSTRAINTS = (
    (
        "roles",
        "ck_roles_code_allowed",
        "code IN ('customer', 'kitchen', 'manager', 'owner')",
    ),
    ("users", "ck_users_email_lower", "email = lower(email)"),
    (
        "locations",
        "ck_locations_preparation_non_negative",
        "preparation_minutes >= 0",
    ),
    ("locations", "ck_locations_capacity_non_negative", "demo_capacity >= 0"),
    (
        "operating_hours",
        "ck_operating_hours_valid_time_range",
        "(is_closed = true AND opens_at IS NULL AND closes_at IS NULL) "
        "OR (is_closed = false AND opens_at IS NOT NULL "
        "AND closes_at IS NOT NULL AND opens_at < closes_at)",
    ),
    ("media_assets", "ck_media_assets_byte_size_positive", "byte_size > 0"),
    (
        "media_assets",
        "ck_media_assets_dimensions_positive",
        "width > 0 AND height > 0",
    ),
    (
        "media_assets",
        "ck_media_assets_focal_point_range",
        "focal_point_x >= 0 AND focal_point_x <= 100 "
        "AND focal_point_y >= 0 AND focal_point_y <= 100",
    ),
    (
        "media_assets",
        "ck_media_assets_publication_state_allowed",
        "publication_state IN ('draft', 'published')",
    ),
    (
        "categories",
        "ck_categories_display_order_non_negative",
        "display_order >= 0",
    ),
    (
        "menu_items",
        "ck_menu_items_currency_code_uppercase",
        "length(currency_code) = 3 AND currency_code = upper(currency_code)",
    ),
    (
        "menu_items",
        "ck_menu_items_publication_state_allowed",
        "publication_state IN ('draft', 'published')",
    ),
    (
        "menu_item_availability",
        "ck_menu_item_availability_state_allowed",
        "state IN ('available', 'temporarily_unavailable', 'scheduled')",
    ),
    (
        "menu_item_availability",
        "ck_menu_item_availability_valid_schedule_range",
        "available_from IS NULL OR available_until IS NULL "
        "OR available_until > available_from",
    ),
    (
        "curated_collections",
        "ck_curated_collections_display_order_non_negative",
        "display_order >= 0",
    ),
    (
        "curated_collections",
        "ck_curated_collections_publication_state_allowed",
        "publication_state IN ('draft', 'published')",
    ),
    (
        "option_groups",
        "ck_option_groups_display_order_non_negative",
        "display_order >= 0",
    ),
    ("options", "ck_options_display_order_non_negative", "display_order >= 0"),
    (
        "home_content",
        "ck_home_content_display_order_non_negative",
        "display_order >= 0",
    ),
    (
        "home_content",
        "ck_home_content_publication_state_allowed",
        "publication_state IN ('draft', 'published')",
    ),
)

INDEXES = (
    ("ix_users_role_id", "users", ("role_id",)),
    ("ix_operating_hours_location_id", "operating_hours", ("location_id",)),
    ("ix_categories_media_id", "categories", ("media_id",)),
    ("ix_menu_items_category_id", "menu_items", ("category_id",)),
    ("ix_menu_items_media_id", "menu_items", ("media_id",)),
    (
        "ix_menu_item_availability_menu_item_id",
        "menu_item_availability",
        ("menu_item_id",),
    ),
    (
        "ix_collection_menu_items_menu_item_id",
        "collection_menu_items",
        ("menu_item_id",),
    ),
    (
        "ix_menu_item_allergens_allergen_id",
        "menu_item_allergens",
        ("allergen_id",),
    ),
    ("ix_option_groups_menu_item_id", "option_groups", ("menu_item_id",)),
    ("ix_options_option_group_id", "options", ("option_group_id",)),
    ("ix_home_content_media_id", "home_content", ("media_id",)),
    ("ix_home_content_menu_item_id", "home_content", ("menu_item_id",)),
)


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE roles SET code = 'owner', label = 'Owner' WHERE code = 'admin'")
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET code = 'manager', label = 'Manager' WHERE code = 'staff'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE users SET email = 'maya@nosh.example' "
            "WHERE email = 'maya@example.test'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE users SET email = 'jordan@nosh.example' "
            "WHERE email = 'jordan@example.test'"
        )
    )

    kitchen_exists = bind.execute(
        sa.text("SELECT 1 FROM roles WHERE code = 'kitchen'")
    ).scalar_one_or_none()
    if kitchen_exists is None:
        roles = sa.table(
            "roles",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
            sa.column("label", sa.String()),
        )
        op.bulk_insert(
            roles,
            [{"id": KITCHEN_ROLE_ID, "code": "kitchen", "label": "Kitchen"}],
        )

    kitchen_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'kitchen'")
    ).scalar_one()
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = :kitchen_role_id "
            "WHERE email = 'kitchen@nosh.example'"
        ),
        {"kitchen_role_id": kitchen_role_id},
    )

    for table_name, constraint_name, condition in CHECK_CONSTRAINTS:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_check_constraint(constraint_name, condition)

    for index_name, table_name, columns in INDEXES:
        op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _ in reversed(INDEXES):
        op.drop_index(index_name, table_name=table_name)

    for table_name, constraint_name, _ in reversed(CHECK_CONSTRAINTS):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="check")

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT id FROM roles WHERE code = 'manager') "
            "WHERE role_id = (SELECT id FROM roles WHERE code = 'kitchen')"
        )
    )
    bind.execute(sa.text("DELETE FROM roles WHERE code = 'kitchen'"))
    bind.execute(
        sa.text("UPDATE roles SET code = 'admin', label = 'Admin' WHERE code = 'owner'")
    )
    bind.execute(
        sa.text(
            "UPDATE roles SET code = 'staff', label = 'Staff' WHERE code = 'manager'"
        )
    )
