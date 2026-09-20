"""Create the Nosh Phase 4 durable data foundation.

Revision ID: 20260920_01
Revises:
Create Date: 2026-09-20 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_01"
down_revision: str | Sequence[str] | None = None
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
        "roles",
        *audit_columns(),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )

    op.create_table(
        "locations",
        *audit_columns(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("address_text", sa.Text(), nullable=False),
        sa.Column("pickup_instructions", sa.Text()),
        sa.Column("delivery_area_text", sa.Text()),
        sa.Column("pickup_available", sa.Boolean(), nullable=False),
        sa.Column("delivery_available", sa.Boolean(), nullable=False),
        sa.Column("preparation_minutes", sa.Integer(), nullable=False),
        sa.Column("demo_capacity", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "slug = lower(slug)", name="ck_locations_location_slug_lower"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_locations"),
        sa.UniqueConstraint("slug", name="uq_locations_slug"),
    )

    op.create_table(
        "media_assets",
        *audit_columns(),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("original_path", sa.String(length=512), nullable=False),
        sa.Column("thumbnail_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("alt_text", sa.String(length=500), nullable=False),
        sa.Column("focal_point_x", sa.Integer(), nullable=False),
        sa.Column("focal_point_y", sa.Integer(), nullable=False),
        sa.Column("source_description", sa.String(length=500)),
        sa.Column("credit", sa.String(length=500)),
        sa.Column("publication_state", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
        sa.UniqueConstraint("checksum_sha256", name="uq_media_assets_checksum_sha256"),
        sa.UniqueConstraint("original_path", name="uq_media_assets_original_path"),
        sa.UniqueConstraint("thumbnail_path", name="uq_media_assets_thumbnail_path"),
    )

    op.create_table(
        "categories",
        *audit_columns(),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("media_id", UUID),
        sa.Column("description", sa.Text()),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "slug = lower(slug)", name="ck_categories_category_slug_lower"
        ),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_assets.id"],
            name="fk_categories_media_id_media_assets",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    op.create_table(
        "allergens",
        *audit_columns(),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.CheckConstraint(
            "slug = lower(slug)", name="ck_allergens_allergen_slug_lower"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_allergens"),
        sa.UniqueConstraint("slug", name="uq_allergens_slug"),
    )

    op.create_table(
        "users",
        *audit_columns(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role_id", UUID, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_users_role_id_roles"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "operating_hours",
        *audit_columns(),
        sa.Column("location_id", UUID, nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.Time()),
        sa.Column("closes_at", sa.Time()),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "weekday >= 0 AND weekday <= 6", name="ck_operating_hours_weekday_range"
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_operating_hours_location_id_locations",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operating_hours"),
        sa.UniqueConstraint(
            "location_id", "weekday", name="uq_operating_hours_location_weekday"
        ),
    )

    op.create_table(
        "menu_items",
        *audit_columns(),
        sa.Column("category_id", UUID, nullable=False),
        sa.Column("media_id", UUID),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ingredients", sa.JSON(), nullable=False),
        sa.Column("dietary_tags", sa.JSON(), nullable=False),
        sa.Column("base_price_minor", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("publication_state", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "base_price_minor >= 0", name="ck_menu_items_base_price_non_negative"
        ),
        sa.CheckConstraint(
            "slug = lower(slug)", name="ck_menu_items_menu_item_slug_lower"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_menu_items_category_id_categories",
        ),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_assets.id"],
            name="fk_menu_items_media_id_media_assets",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menu_items"),
        sa.UniqueConstraint("slug", name="uq_menu_items_slug"),
    )

    op.create_table(
        "menu_item_availability",
        *audit_columns(),
        sa.Column("location_id", UUID, nullable=False),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("available_from", TIMESTAMP),
        sa.Column("available_until", TIMESTAMP),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_menu_item_availability_location_id_locations",
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_menu_item_availability_menu_item_id_menu_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menu_item_availability"),
        sa.UniqueConstraint(
            "location_id",
            "menu_item_id",
            name="uq_menu_item_availability_location_item",
        ),
    )

    op.create_table(
        "curated_collections",
        *audit_columns(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("publication_state", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "slug = lower(slug)", name="ck_curated_collections_collection_slug_lower"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_curated_collections"),
        sa.UniqueConstraint("slug", name="uq_curated_collections_slug"),
    )

    op.create_table(
        "collection_menu_items",
        *audit_columns(),
        sa.Column("collection_id", UUID, nullable=False),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["curated_collections.id"],
            name="fk_collection_menu_items_collection_id_curated_collections",
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_collection_menu_items_menu_item_id_menu_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_collection_menu_items"),
        sa.UniqueConstraint(
            "collection_id",
            "menu_item_id",
            name="uq_collection_menu_items_collection_item",
        ),
    )

    op.create_table(
        "menu_item_allergens",
        *audit_columns(),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.Column("allergen_id", UUID, nullable=False),
        sa.Column("note", sa.String(length=500)),
        sa.ForeignKeyConstraint(
            ["allergen_id"],
            ["allergens.id"],
            name="fk_menu_item_allergens_allergen_id_allergens",
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_menu_item_allergens_menu_item_id_menu_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_menu_item_allergens"),
        sa.UniqueConstraint(
            "menu_item_id", "allergen_id", name="uq_menu_item_allergens_item_allergen"
        ),
    )

    op.create_table(
        "option_groups",
        *audit_columns(),
        sa.Column("menu_item_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("minimum_selections", sa.Integer(), nullable=False),
        sa.Column("maximum_selections", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "maximum_selections >= minimum_selections",
            name="ck_option_groups_maximum_gte_minimum",
        ),
        sa.CheckConstraint(
            "minimum_selections >= 0", name="ck_option_groups_minimum_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_option_groups_menu_item_id_menu_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_option_groups"),
    )

    op.create_table(
        "options",
        *audit_columns(),
        sa.Column("option_group_id", UUID, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("price_delta_minor", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "price_delta_minor >= 0", name="ck_options_price_delta_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["option_group_id"],
            ["option_groups.id"],
            name="fk_options_option_group_id_option_groups",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_options"),
    )

    op.create_table(
        "home_content",
        *audit_columns(),
        sa.Column("content_key", sa.String(length=80), nullable=False),
        sa.Column("heading", sa.String(length=240), nullable=False),
        sa.Column("supporting_copy", sa.Text(), nullable=False),
        sa.Column("action_label", sa.String(length=100)),
        sa.Column("action_href", sa.String(length=255)),
        sa.Column("media_id", UUID),
        sa.Column("menu_item_id", UUID),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("publication_state", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_assets.id"],
            name="fk_home_content_media_id_media_assets",
        ),
        sa.ForeignKeyConstraint(
            ["menu_item_id"],
            ["menu_items.id"],
            name="fk_home_content_menu_item_id_menu_items",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_home_content"),
        sa.UniqueConstraint("content_key", name="uq_home_content_content_key"),
    )


def downgrade() -> None:
    op.drop_table("home_content")
    op.drop_table("options")
    op.drop_table("option_groups")
    op.drop_table("menu_item_allergens")
    op.drop_table("collection_menu_items")
    op.drop_table("curated_collections")
    op.drop_table("menu_item_availability")
    op.drop_table("menu_items")
    op.drop_table("operating_hours")
    op.drop_table("users")
    op.drop_table("allergens")
    op.drop_table("categories")
    op.drop_table("media_assets")
    op.drop_table("locations")
    op.drop_table("roles")
