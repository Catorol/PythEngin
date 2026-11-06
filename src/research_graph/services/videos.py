from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from research_graph.api.errors import (
    BadRequestError,
    ConflictError,
    InvalidStateTransitionError,
    NotFoundError,
)
from research_graph.models import Creator, Hook, Prediction, Product, Video
from research_graph.schemas.video import VideoCreate, VideoUpdate
from research_graph.services.common import order_by, paginate

# Правило: допустимые переходы статусов видео.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"published", "archived"},
    "published": {"boosted", "archived"},
    "boosted": {"archived"},
    "archived": set(),
}

SORT_FIELDS: dict[str, Any] = {
    "id": Video.id,
    "created_at": Video.created_at,
    "published_at": Video.published_at,
    "length_seconds": Video.length_seconds,
}


def check_transition(current: str, new: str) -> None:
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidStateTransitionError(
            f"Переход {current} -> {new} запрещён",
            details={"allowed": sorted(ALLOWED_TRANSITIONS.get(current, set()))},
        )


def list_videos(
    db: Session,
    *,
    page: int,
    size: int,
    status: str | None = None,
    creator_id: int | None = None,
    video_format: str | None = None,
    viral_flag: int | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    sort_by: str = "id",
    order: str = "asc",
) -> tuple[list[Video], int]:
    stmt = select(Video).options(selectinload(Video.hooks))
    if status:
        stmt = stmt.where(Video.status == status)
    if creator_id is not None:
        stmt = stmt.where(Video.creator_id == creator_id)
    if video_format:
        stmt = stmt.where(Video.video_format == video_format)
    if viral_flag is not None:
        stmt = stmt.where(Video.viral_flag == viral_flag)
    if published_from:
        stmt = stmt.where(Video.published_at >= published_from)
    if published_to:
        stmt = stmt.where(Video.published_at <= published_to)
    stmt = stmt.order_by(order_by(SORT_FIELDS[sort_by], order), Video.id)
    return paginate(db, stmt, page, size)


def get_video(db: Session, video_id: int) -> Video:
    video = db.scalar(
        select(Video).options(selectinload(Video.hooks)).where(Video.id == video_id)
    )
    if video is None:
        raise NotFoundError(f"Видео {video_id} не найдено")
    return video


def _resolve_hooks(db: Session, codes: list[str]) -> list[Hook]:
    if not codes:
        return []
    hooks = list(db.scalars(select(Hook).where(Hook.code.in_(codes))))
    unknown = sorted(set(codes) - {h.code for h in hooks})
    if unknown:
        raise BadRequestError(f"Неизвестные хуки: {', '.join(unknown)}", details=unknown)
    return hooks


def create_video(db: Session, data: VideoCreate) -> Video:
    if db.get(Creator, data.creator_id) is None:
        raise NotFoundError(f"Креатор {data.creator_id} не найден")
    if db.get(Product, data.product_id) is None:
        raise NotFoundError(f"Товар {data.product_id} не найден")
    if db.scalar(select(Video.id).where(Video.external_id == data.external_id)) is not None:
        raise ConflictError(f"Видео с external_id={data.external_id} уже существует")
    hooks = _resolve_hooks(db, data.hook_codes)

    video = Video(
        **data.model_dump(exclude={"hook_codes"}),
        status="draft",
    )
    video.hooks = hooks
    db.add(video)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Видео нарушает ограничения БД") from exc
    return get_video(db, video.id)


def update_video(db: Session, video_id: int, data: VideoUpdate) -> Video:
    video = get_video(db, video_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True, exclude={"hook_codes"})
    for key, value in changes.items():
        setattr(video, key, value)
    if data.hook_codes is not None:
        video.hooks = _resolve_hooks(db, data.hook_codes)
    db.commit()
    return get_video(db, video_id)


def delete_video(db: Session, video_id: int) -> None:
    video = get_video(db, video_id)
    db.delete(video)
    db.commit()


def latest_prediction(db: Session, video_id: int) -> Prediction | None:
    return db.scalar(
        select(Prediction)
        .where(Prediction.video_id == video_id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .limit(1)
    )


def change_status(db: Session, video_id: int, new_status: str) -> Video:
    """Правила: допустимые переходы; усилить (boosted) можно только при рекомендации boost."""
    video = get_video(db, video_id)
    check_transition(video.status, new_status)
    if new_status == "boosted":
        prediction = latest_prediction(db, video_id)
        if prediction is None or prediction.recommendation != "boost":
            raise InvalidStateTransitionError(
                "Нельзя усилить видео: нет предсказания с рекомендацией 'boost'"
            )
    video.status = new_status
    db.commit()
    return get_video(db, video_id)
