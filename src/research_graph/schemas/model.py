from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    filename: str
    algorithm: str | None
    roc_auc: float | None
    is_active: bool
    metrics: dict[str, Any] | None
    created_at: datetime


class ModelUploadResponse(BaseModel):
    status: Literal["success"] = "success"
    model: ModelVersionRead
