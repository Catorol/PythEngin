from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from research_graph.db import Base

if TYPE_CHECKING:
    from research_graph.models.video import Video


class Creator(Base):
    __tablename__ = "creators"
    __table_args__ = (
        CheckConstraint("followers >= 0", name="followers_non_negative"),
        CheckConstraint("engagement_rate >= 0", name="engagement_rate_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    tier: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    country: Mapped[str] = mapped_column(String(64), index=True)
    followers: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    videos: Mapped[list["Video"]] = relationship(back_populates="creator")
