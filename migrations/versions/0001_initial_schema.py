"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=64), nullable=False),
        sa.Column("followers", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("engagement_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("followers >= 0", name=op.f("ck_creators_followers_non_negative")),
        sa.CheckConstraint(
            "engagement_rate >= 0", name=op.f("ck_creators_engagement_rate_non_negative")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creators")),
        sa.UniqueConstraint("external_id", name=op.f("uq_creators_external_id")),
    )
    op.create_index(op.f("ix_creators_tier"), "creators", ["tier"])
    op.create_index(op.f("ix_creators_category"), "creators", ["category"])
    op.create_index(op.f("ix_creators_country"), "creators", ["country"])

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("subcategory", sa.String(length=64), nullable=True),
        sa.Column("brand_type", sa.String(length=64), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("price >= 0", name=op.f("ck_products_price_non_negative")),
        sa.CheckConstraint("rating BETWEEN 0 AND 5", name=op.f("ck_products_rating_range")),
        sa.CheckConstraint("review_count >= 0", name=op.f("ck_products_review_count_non_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("external_id", name=op.f("uq_products_external_id")),
    )
    op.create_index(op.f("ix_products_category"), "products", ["category"])

    op.create_table(
        "hooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hooks")),
        sa.UniqueConstraint("code", name=op.f("uq_hooks_code")),
    )

    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("algorithm", sa.String(length=64), nullable=True),
        sa.Column("roc_auc", sa.Float(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("roc_auc BETWEEN 0 AND 1", name=op.f("ck_model_versions_roc_auc_range")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_versions")),
        sa.UniqueConstraint("filename", name=op.f("uq_model_versions_filename")),
    )
    op.create_index(
        "uq_model_versions_single_active",
        "model_versions",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active"),
    )

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("title_type", sa.String(length=64), nullable=True),
        sa.Column("video_format", sa.String(length=64), nullable=True),
        sa.Column("length_seconds", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="published", nullable=False),
        sa.Column("viral_flag", sa.SmallInteger(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'boosted', 'archived')",
            name=op.f("ck_videos_status_valid"),
        ),
        sa.CheckConstraint("length_seconds > 0", name=op.f("ck_videos_length_positive")),
        sa.CheckConstraint("viral_flag IN (0, 1)", name=op.f("ck_videos_viral_flag_binary")),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["creators.id"],
            name=op.f("fk_videos_creator_id_creators"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_videos_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos")),
        sa.UniqueConstraint("external_id", name=op.f("uq_videos_external_id")),
    )
    op.create_index(op.f("ix_videos_creator_id"), "videos", ["creator_id"])
    op.create_index(op.f("ix_videos_product_id"), "videos", ["product_id"])
    op.create_index(op.f("ix_videos_video_format"), "videos", ["video_format"])
    op.create_index(op.f("ix_videos_published_at"), "videos", ["published_at"])
    op.create_index(op.f("ix_videos_status"), "videos", ["status"])
    op.create_index(op.f("ix_videos_viral_flag"), "videos", ["viral_flag"])

    op.create_table(
        "video_hooks",
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("hook_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name=op.f("fk_video_hooks_video_id_videos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hook_id"],
            ["hooks.id"],
            name=op.f("fk_video_hooks_hook_id_hooks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("video_id", "hook_id", name=op.f("pk_video_hooks")),
    )
    op.create_index("ix_video_hooks_hook_id", "video_hooks", ["hook_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=True),
        sa.Column("model_version_id", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("predicted_flag", sa.SmallInteger(), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "probability BETWEEN 0 AND 1", name=op.f("ck_predictions_probability_range")
        ),
        sa.CheckConstraint(
            "predicted_flag IN (0, 1)", name=op.f("ck_predictions_predicted_flag_binary")
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name=op.f("fk_predictions_video_id_videos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["model_versions.id"],
            name=op.f("fk_predictions_model_version_id_model_versions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predictions")),
    )
    op.create_index(op.f("ix_predictions_video_id"), "predictions", ["video_id"])
    op.create_index(op.f("ix_predictions_model_version_id"), "predictions", ["model_version_id"])
    op.create_index(op.f("ix_predictions_created_at"), "predictions", ["created_at"])


def downgrade() -> None:
    op.drop_table("predictions")
    op.drop_table("video_hooks")
    op.drop_table("videos")
    op.drop_table("model_versions")
    op.drop_table("hooks")
    op.drop_table("products")
    op.drop_table("creators")
