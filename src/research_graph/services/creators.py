from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_graph.api.errors import ConflictError, NotFoundError
from research_graph.models import Creator, Video
from research_graph.schemas.creator import CreatorCreate, CreatorUpdate
from research_graph.services.common import order_by, paginate

SORT_FIELDS: dict[str, Any] = {
    "id": Creator.id,
    "followers": Creator.followers,
    "engagement_rate": Creator.engagement_rate,
    "created_at": Creator.created_at,
}


def list_creators(
    db: Session,
    *,
    page: int,
    size: int,
    tier: str | None = None,
    category: str | None = None,
    country: str | None = None,
    sort_by: str = "id",
    order: str = "asc",
) -> tuple[list[Creator], int]:
    stmt = select(Creator)
    if tier:
        stmt = stmt.where(Creator.tier == tier)
    if category:
        stmt = stmt.where(Creator.category == category)
    if country:
        stmt = stmt.where(Creator.country == country)
    stmt = stmt.order_by(order_by(SORT_FIELDS[sort_by], order), Creator.id)
    return paginate(db, stmt, page, size)


def get_creator(db: Session, creator_id: int) -> Creator:
    creator = db.get(Creator, creator_id)
    if creator is None:
        raise NotFoundError(f"Креатор {creator_id} не найден")
    return creator


def create_creator(db: Session, data: CreatorCreate) -> Creator:
    exists = db.scalar(select(Creator.id).where(Creator.external_id == data.external_id))
    if exists is not None:
        raise ConflictError(f"Креатор с external_id={data.external_id} уже существует")
    creator = Creator(**data.model_dump())
    db.add(creator)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Креатор нарушает ограничения БД") from exc
    return creator


def update_creator(db: Session, creator_id: int, data: CreatorUpdate) -> Creator:
    creator = get_creator(db, creator_id)
    for key, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(creator, key, value)
    db.commit()
    return creator


def delete_creator(db: Session, creator_id: int) -> None:
    """Правило: нельзя удалить креатора, у которого есть видео."""
    creator = get_creator(db, creator_id)
    has_videos = db.scalar(select(Video.id).where(Video.creator_id == creator_id).limit(1))
    if has_videos is not None:
        raise ConflictError("Нельзя удалить креатора: у него есть видео")
    db.delete(creator)
    db.commit()
