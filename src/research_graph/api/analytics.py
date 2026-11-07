from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from research_graph.api.deps import DbSession
from research_graph.schemas.analytics import CreatorStat, HookStat, TrendPoint
from research_graph.services import analytics as service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/virality-by-hook", response_model=list[HookStat], summary="Виральность по типам хуков"
)
def virality_by_hook(db: DbSession, min_videos: Annotated[int, Query(ge=1)] = 1) -> list[HookStat]:
    """Для каждого хука: число видео, число виральных и доля виральных."""
    return service.virality_by_hook(db, min_videos=min_videos)


@router.get("/top-creators", response_model=list[CreatorStat], summary="Топ креаторов")
def top_creators(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    min_videos: Annotated[int, Query(ge=1)] = 5,
) -> list[CreatorStat]:
    """Топ-N креаторов по доле виральных видео (учитываются креаторы с min_videos и более)."""
    return service.top_creators(db, limit=limit, min_videos=min_videos)


@router.get("/viral-trend", response_model=list[TrendPoint], summary="Динамика по месяцам")
def viral_trend(
    db: DbSession, published_from: date | None = None, published_to: date | None = None
) -> list[TrendPoint]:
    """Число видео и доля виральных по месяцам публикации."""
    return service.viral_trend(db, published_from=published_from, published_to=published_to)
