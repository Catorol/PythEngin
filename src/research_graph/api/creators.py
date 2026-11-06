from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response

from research_graph.api.deps import DbSession
from research_graph.api.errors import ErrorResponse, ResponsesDict
from research_graph.schemas.common import Page, SortOrder
from research_graph.schemas.creator import CreatorCreate, CreatorRead, CreatorUpdate
from research_graph.services import creators as service

router = APIRouter(prefix="/creators", tags=["creators"])

NOT_FOUND: ResponsesDict = {404: {"model": ErrorResponse, "description": "Креатор не найден"}}
CONFLICT: ResponsesDict = {409: {"model": ErrorResponse, "description": "Конфликт данных"}}


@router.get("", response_model=Page[CreatorRead], summary="Список креаторов")
def list_creators(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    tier: str | None = None,
    category: str | None = None,
    country: str | None = None,
    sort_by: Literal["id", "followers", "engagement_rate", "created_at"] = "id",
    order: SortOrder = "asc",
) -> Page[CreatorRead]:
    """Пагинация, фильтры по tier/category/country и сортировка."""
    items, total = service.list_creators(
        db,
        page=page,
        size=size,
        tier=tier,
        category=category,
        country=country,
        sort_by=sort_by,
        order=order,
    )
    return Page[CreatorRead](
        items=[CreatorRead.model_validate(i) for i in items], total=total, page=page, size=size
    )


@router.post(
    "",
    response_model=CreatorRead,
    status_code=201,
    responses=CONFLICT,
    summary="Создать креатора",
)
def create_creator(data: CreatorCreate, db: DbSession) -> CreatorRead:
    return CreatorRead.model_validate(service.create_creator(db, data))


@router.get("/{creator_id}", response_model=CreatorRead, responses=NOT_FOUND, summary="Креатор")
def get_creator(creator_id: int, db: DbSession) -> CreatorRead:
    return CreatorRead.model_validate(service.get_creator(db, creator_id))


@router.patch(
    "/{creator_id}", response_model=CreatorRead, responses=NOT_FOUND, summary="Изменить креатора"
)
def update_creator(creator_id: int, data: CreatorUpdate, db: DbSession) -> CreatorRead:
    return CreatorRead.model_validate(service.update_creator(db, creator_id, data))


@router.delete(
    "/{creator_id}",
    status_code=204,
    responses={**NOT_FOUND, **CONFLICT},
    summary="Удалить креатора",
)
def delete_creator(creator_id: int, db: DbSession) -> Response:
    """Нельзя удалить креатора, у которого есть видео (409)."""
    service.delete_creator(db, creator_id)
    return Response(status_code=204)
