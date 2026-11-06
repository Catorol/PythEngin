from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    external_id: str = Field(min_length=1, max_length=64, examples=["PROD_XT8XBC34"])
    category: str = Field(min_length=1, max_length=64, examples=["Beauty"])
    subcategory: str | None = Field(default=None, max_length=64, examples=["Skincare"])
    brand_type: str | None = Field(default=None, max_length=64, examples=["Premium"])
    price: float = Field(ge=0, examples=[24.9])
    rating: float | None = Field(default=None, ge=0, le=5, examples=[4.6])
    review_count: int = Field(default=0, ge=0, examples=[1200])


class ProductRead(ProductCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
