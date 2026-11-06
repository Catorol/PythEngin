from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_graph.db import Base

if TYPE_CHECKING:
    from research_graph.models.creator import Creator
    from research_graph.models.ml import Prediction
    from research_graph.models.product import Product

VIDEO_STATUSES = ("draft", "published", "boosted", "archived")

video_hooks = Table(
    "video_hooks",
    Base.metadata,
    Column("video_id", ForeignKey("videos.id", ondelete="CASCADE"), primary_key=True),
    Column("hook_id", ForeignKey("hooks.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_video_hooks_hook_id", "hook_id"),
)


class Hook(Base):
    __tablename__ = "hooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(128))

    videos: Mapped[list["Video"]] = relationship(secondary=video_hooks, back_populates="hooks")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'boosted', 'archived')", name="status_valid"
        ),
        CheckConstraint("length_seconds > 0", name="length_positive"),
        CheckConstraint("viral_flag IN (0, 1)", name="viral_flag_binary"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    creator_id: Mapped[int] = mapped_column(
        ForeignKey("creators.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    title_type: Mapped[Optional[str]] = mapped_column(String(64))
    video_format: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    length_seconds: Mapped[int] = mapped_column(Integer)
    published_at: Mapped[Optional[date]] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default="published", server_default="published", index=True
    )
    viral_flag: Mapped[Optional[int]] = mapped_column(SmallInteger, index=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator: Mapped["Creator"] = relationship(back_populates="videos")
    product: Mapped["Product"] = relationship(back_populates="videos")
    hooks: Mapped[list[Hook]] = relationship(secondary=video_hooks, back_populates="videos")
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="video", cascade="all, delete-orphan", passive_deletes=True
    )
