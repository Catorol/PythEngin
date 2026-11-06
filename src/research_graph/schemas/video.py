from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

VideoStatus = Literal["draft", "published", "boosted", "archived"]


class HookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    title: str


class VideoCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "external_id": "VID_Z74E5XMM",
                    "creator_id": 1,
                    "product_id": 1,
                    "video_format": "Tutorial",
                    "title_type": "Question",
                    "length_seconds": 30,
                    "published_at": "2025-10-06",
                    "hook_codes": ["demo_hook", "story_hook"],
                    "features": {"creator_engagement_rate": 6.5},
                }
            ]
        }
    )

    external_id: str = Field(min_length=1, max_length=64)
    creator_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    title_type: str | None = Field(default=None, max_length=64)
    video_format: str | None = Field(default=None, max_length=64)
    length_seconds: int = Field(gt=0, le=600, description="Длительность, секунды")
    published_at: date | None = None
    hook_codes: list[str] = Field(default_factory=list, description="Коды хуков из /hooks")
    features: dict[str, Any] = Field(default_factory=dict, description="Признаки для модели")


class VideoUpdate(BaseModel):
    title_type: str | None = Field(default=None, max_length=64)
    video_format: str | None = Field(default=None, max_length=64)
    length_seconds: int | None = Field(default=None, gt=0, le=600)
    published_at: date | None = None
    hook_codes: list[str] | None = None
    features: dict[str, Any] | None = None


class VideoStatusUpdate(BaseModel):
    status: VideoStatus = Field(examples=["published"])


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    creator_id: int
    product_id: int
    title_type: str | None
    video_format: str | None
    length_seconds: int
    published_at: date | None
    status: VideoStatus
    viral_flag: int | None
    hooks: list[HookRead]
    created_at: datetime


class VideoDetail(VideoRead):
    features: dict[str, Any]
