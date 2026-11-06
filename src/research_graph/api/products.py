from typing import Annotated

from fastapi import APIRouter, Query

from research_graph.api.deps import DbSession
from research_graph.api.errors import ErrorResponse
from research_graph.schemas.common import Page
from research_graph.schemas.product import ProductCreate, ProductRead
from research_graph.schemas.video import HookRead
from research_graph.services import products as service

router = APIRouter(tags=["products"])


@router.get("/products", response_model=Page[ProductRead], summary="Список товаров")
def list_products(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
) -> Page[ProductRead]:
    items, total = service.list_products(db, page=page, size=size, category=category)
    return Page[ProductRead](
        items=[ProductRead.model_validate(i) for i in items], total=total, page=page, size=size
    )


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=201,
    responses={409: {"model": ErrorResponse}},
    summary="Создать товар",
)
def create_product(data: ProductCreate, db: DbSession) -> ProductRead:
    return ProductRead.model_validate(service.create_product(db, data))


@router.get(
    "/products/{product_id}",
    response_model=ProductRead,
    responses={404: {"model": ErrorResponse}},
    summary="Товар",
)
def get_product(product_id: int, db: DbSession) -> ProductRead:
    return ProductRead.model_validate(service.get_product(db, product_id))


@router.get("/hooks", response_model=list[HookRead], summary="Справочник хуков")
def list_hooks(db: DbSession) -> list[HookRead]:
    return [HookRead.model_validate(h) for h in service.list_hooks(db)]
