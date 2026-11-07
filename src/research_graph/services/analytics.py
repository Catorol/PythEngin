"""Аналитические запросы с агрегациями."""

from datetime import date

from sqlalchemy import Float, cast, desc, extract, func, select
from sqlalchemy.orm import Session

from research_graph.models import Creator, Hook, Video
from research_graph.models.video import video_hooks
from research_graph.schemas.analytics import CreatorStat, HookStat, TrendPoint


def _int(value: int | None) -> int:
    return int(value or 0)


def _rate(viral: int, total: int) -> float:
    return round(viral / total, 4) if total else 0.0


def virality_by_hook(db: Session, *, min_videos: int = 1) -> list[HookStat]:
    """Доля виральных видео для каждого типа хука (по убыванию доли)."""
    viral = func.coalesce(func.sum(Video.viral_flag), 0)
    stmt = (
        select(Hook.code, Hook.title, func.count(Video.id), viral)
        .join(video_hooks, video_hooks.c.hook_id == Hook.id)
        .join(Video, Video.id == video_hooks.c.video_id)
        .where(Video.viral_flag.is_not(None))
        .group_by(Hook.id, Hook.code, Hook.title)
        .having(func.count(Video.id) >= min_videos)
    )
    stats = [
        HookStat(
            hook_code=code,
            hook_title=title,
            videos=_int(total),
            viral_videos=_int(v),
            viral_rate=_rate(_int(v), _int(total)),
        )
        for code, title, total, v in db.execute(stmt)
    ]
    return sorted(stats, key=lambda s: (-s.viral_rate, -s.videos, s.hook_code))


def top_creators(db: Session, *, limit: int = 10, min_videos: int = 5) -> list[CreatorStat]:
    """Топ-N креаторов по доле виральных видео."""
    total = func.count(Video.id)
    viral = func.coalesce(func.sum(Video.viral_flag), 0)
    rate = cast(viral, Float) / total
    stmt = (
        select(Creator.id, Creator.external_id, Creator.tier, Creator.followers, total, viral)
        .join(Video, Video.creator_id == Creator.id)
        .where(Video.viral_flag.is_not(None))
        .group_by(Creator.id, Creator.external_id, Creator.tier, Creator.followers)
        .having(total >= min_videos)
        .order_by(desc(rate), desc(total), Creator.id)
        .limit(limit)
    )
    return [
        CreatorStat(
            creator_id=cid,
            external_id=ext,
            tier=tier,
            followers=_int(followers),
            videos=_int(n),
            viral_videos=_int(v),
            viral_rate=_rate(_int(v), _int(n)),
        )
        for cid, ext, tier, followers, n, v in db.execute(stmt)
    ]


def viral_trend(
    db: Session, *, published_from: date | None = None, published_to: date | None = None
) -> list[TrendPoint]:
    """Динамика по месяцам: число видео и доля виральных."""
    year = extract("year", Video.published_at)
    month = extract("month", Video.published_at)
    viral = func.coalesce(func.sum(Video.viral_flag), 0)
    stmt = select(year, month, func.count(Video.id), viral).where(
        Video.published_at.is_not(None), Video.viral_flag.is_not(None)
    )
    if published_from:
        stmt = stmt.where(Video.published_at >= published_from)
    if published_to:
        stmt = stmt.where(Video.published_at <= published_to)
    stmt = stmt.group_by(year, month).order_by(year, month)
    return [
        TrendPoint(
            period=f"{_int(y):04d}-{_int(m):02d}",
            videos=_int(n),
            viral_videos=_int(v),
            viral_rate=_rate(_int(v), _int(n)),
        )
        for y, m, n, v in db.execute(stmt)
    ]
