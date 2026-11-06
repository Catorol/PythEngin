from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_graph.db import Base

if TYPE_CHECKING:
    from research_graph.models.video import Video


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        CheckConstraint("roc_auc BETWEEN 0 AND 1", name="roc_auc_range"),
        # В БД может быть только одна активная модель.
        Index(
            "uq_model_versions_single_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    filename: Mapped[str] = mapped_column(String(255), unique=True)
    algorithm: Mapped[Optional[str]] = mapped_column(String(64))
    roc_auc: Mapped[Optional[float]] = mapped_column(Float)
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="model_version")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("probability BETWEEN 0 AND 1", name="probability_range"),
        CheckConstraint("predicted_flag IN (0, 1)", name="predicted_flag_binary"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), index=True
    )
    model_version_id: Mapped[int] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"), index=True
    )
    probability: Mapped[float] = mapped_column(Float)
    predicted_flag: Mapped[int] = mapped_column(SmallInteger)
    recommendation: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    video: Mapped[Optional["Video"]] = relationship(back_populates="predictions")
    model_version: Mapped[ModelVersion] = relationship(back_populates="predictions")
