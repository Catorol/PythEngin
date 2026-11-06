from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

SortOrder = Literal["asc", "desc"]


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
