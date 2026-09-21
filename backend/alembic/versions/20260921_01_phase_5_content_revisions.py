"""Add durable home-content revisions for the Phase 5 authoring workflow.

Revision ID: 20260921_01
Revises: 20260920_02
Create Date: 2026-09-21 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_01"
down_revision: str | Sequence[str] | None = "20260920_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "home_content_revisions",
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
        sa.Column("home_content_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid()),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "action IN ('draft_saved', 'published')",
            name="ck_home_content_revisions_action_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_home_content_revisions_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["home_content_id"],
            ["home_content.id"],
            name="fk_home_content_revisions_home_content_id_home_content",
        ),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["media_assets.id"],
            name="fk_home_content_revisions_media_id_media_assets",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_home_content_revisions"),
    )
    op.create_index(
        "ix_home_content_revisions_home_content_id",
        "home_content_revisions",
        ["home_content_id"],
    )
    op.create_index(
        "ix_home_content_revisions_actor_id",
        "home_content_revisions",
        ["actor_id"],
    )
    op.create_index(
        "ix_home_content_revisions_media_id",
        "home_content_revisions",
        ["media_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_home_content_revisions_media_id", table_name="home_content_revisions"
    )
    op.drop_index(
        "ix_home_content_revisions_actor_id", table_name="home_content_revisions"
    )
    op.drop_index(
        "ix_home_content_revisions_home_content_id",
        table_name="home_content_revisions",
    )
    op.drop_table("home_content_revisions")
