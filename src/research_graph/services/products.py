from sqlalchemy import select
from sqlalchemy.orm import Session

from research_graph.api.errors import ConflictError, NotFoundError
from research_graph.models import Hook, Product
from research_graph.schemas.product import ProductCreate
from research_graph.services.common import paginate


def list_products(
    db: Session, *, page: int, size: int, category: str | None = None
) -> tuple[list[Product], int]:
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category == category)
    return paginate(db, stmt.order_by(Product.id), page, size)


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Товар {product_id} не найден")
    return product


def create_product(db: Session, data: ProductCreate) -> Product:
    exists = db.scalar(select(Product.id).where(Product.external_id == data.external_id))
    if exists is not None:
        raise ConflictError(f"Товар с external_id={data.external_id} уже существует")
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    return product


def list_hooks(db: Session) -> list[Hook]:
    return list(db.scalars(select(Hook).order_by(Hook.code)))
