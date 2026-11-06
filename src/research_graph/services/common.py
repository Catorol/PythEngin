from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session


def paginate(db: Session, stmt: Select[Any], page: int, size: int) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.limit(size).offset((page - 1) * size)))
    return items, total


def order_by(column: InstrumentedAttribute[Any], order: str) -> Any:
    return column.desc() if order == "desc" else column.asc()
