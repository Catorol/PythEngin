from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatorBase(BaseModel):
    tier: str = Field(min_length=1, max_length=32, description="Уровень", examples=["Micro"])
    category: str = Field(min_length=1, max_length=64, description="Тематика", examples=["Beauty"])
    country: str = Field(min_length=1, max_length=64, description="Страна", examples=["US"])
    followers: int = Field(ge=0, description="Число подписчиков", examples=[120000])
    engagement_rate: float = Field(ge=0, description="Вовлечённость, %", examples=[6.5])


class CreatorCreate(CreatorBase):
    external_id: str = Field(min_length=1, max_length=64, examples=["CRT_1K4UMPDP"])


class CreatorUpdate(BaseModel):
    tier: str | None = Field(default=None, min_length=1, max_length=32)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    country: str | None = Field(default=None, min_length=1, max_length=64)
    followers: int | None = Field(default=None, ge=0)
    engagement_rate: float | None = Field(default=None, ge=0)


class CreatorRead(CreatorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    created_at: datetime
