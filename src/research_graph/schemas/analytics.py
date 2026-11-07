from pydantic import BaseModel


class HookStat(BaseModel):
    hook_code: str
    hook_title: str
    videos: int
    viral_videos: int
    viral_rate: float


class CreatorStat(BaseModel):
    creator_id: int
    external_id: str
    tier: str
    followers: int
    videos: int
    viral_videos: int
    viral_rate: float


class TrendPoint(BaseModel):
    period: str
    videos: int
    viral_videos: int
    viral_rate: float
