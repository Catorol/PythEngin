from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from research_graph.api.deps import DbSession
from research_graph.api.errors import ErrorResponse
from research_graph.schemas.common import Page, SortOrder
from research_graph.schemas.video import (
    VideoCreate,
    VideoDetail,
    VideoRead,
    VideoStatus,
    VideoStatusUpdate,
    VideoUpdate,
)
from research_graph.services import videos as service

router = APIRouter(prefix="/videos", tags=["videos"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Не найдено"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Конфликт или запрещённый переход"}}


@router.get("", response_model=Page[VideoRead], summary="Список видео")
def list_videos(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: VideoStatus | None = None,
    creator_id: int | None = None,
    video_format: str | None = None,
    viral_flag: Annotated[int | None, Query(ge=0, le=1)] = None,
    published_from: date | None = None,
    published_to: date | None = None,
    sort_by: Literal["id", "created_at", "published_at", "length_seconds"] = "id",
    order: SortOrder = "asc",
) -> Page[VideoRead]:
    """Пагинация, фильтры (статус, креатор, формат, виральность, даты) и сортировка."""
    items, total = service.list_videos(
        db,
        page=page,
        size=size,
        status=status,
        creator_id=creator_id,
        video_format=video_format,
        viral_flag=viral_flag,
        published_from=published_from,
        published_to=published_to,
        sort_by=sort_by,
        order=order,
    )
    return Page[VideoRead](
        items=[VideoRead.model_validate(i) for i in items], total=total, page=page, size=size
    )


@router.post(
    "",
    response_model=VideoDetail,
    status_code=201,
    responses={**NOT_FOUND, **CONFLICT, 400: {"model": ErrorResponse}},
    summary="Создать видео (статус draft)",
)
def create_video(data: VideoCreate, db: DbSession) -> VideoDetail:
    return VideoDetail.model_validate(service.create_video(db, data))


@router.get("/{video_id}", response_model=VideoDetail, responses=NOT_FOUND, summary="Видео")
def get_video(video_id: int, db: DbSession) -> VideoDetail:
    return VideoDetail.model_validate(service.get_video(db, video_id))


@router.patch(
    "/{video_id}", response_model=VideoDetail, responses=NOT_FOUND, summary="Изменить видео"
)
def update_video(video_id: int, data: VideoUpdate, db: DbSession) -> VideoDetail:
    return VideoDetail.model_validate(service.update_video(db, video_id, data))


@router.delete("/{video_id}", status_code=204, responses=NOT_FOUND, summary="Удалить видео")
def delete_video(video_id: int, db: DbSession) -> Response:
    service.delete_video(db, video_id)
    return Response(status_code=204)


@router.patch(
    "/{video_id}/status",
    response_model=VideoDetail,
    responses={**NOT_FOUND, **CONFLICT},
    summary="Сменить статус видео",
)
def change_video_status(video_id: int, data: VideoStatusUpdate, db: DbSession) -> VideoDetail:
    """Допустимые переходы: draft->published/archived, published->boosted/archived,
    boosted->archived. В boosted можно перейти только при рекомендации `boost`."""
    return VideoDetail.model_validate(service.change_status(db, video_id, data.status))
