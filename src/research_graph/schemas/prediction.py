from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model, field_validator

from research_graph.ml.features import CATEGORICAL_FEATURES, FLAG_FEATURES, NUMERIC_FEATURES


def _build_features_model() -> type[BaseModel]:
    """Модель одной записи: все признаки необязательны, типы проверяются."""
    fields: dict[str, Any] = {}
    for name in NUMERIC_FEATURES:
        fields[name] = (float | None, Field(default=None))
    for name in FLAG_FEATURES:
        fields[name] = (int | None, Field(default=None, ge=0, le=1))
    for name in CATEGORICAL_FEATURES:
        fields[name] = (str | None, Field(default=None))
    return create_model("VideoFeatures", __config__=ConfigDict(extra="forbid"), **fields)


VideoFeatures = _build_features_model()


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "records": [
                        {
                            "creator_followers": 120000,
                            "creator_engagement_rate": 6.5,
                            "creator_tier": "Micro",
                            "video_format": "Tutorial",
                            "hook_type": "Curiosity",
                            "hook_demo_hook_flag": 1,
                        }
                    ]
                }
            ]
        }
    )

    records: list[dict[str, Any]] = Field(
        min_length=1,
        max_length=1000,
        description="Одна или несколько записей с признаками (любое подмножество признаков модели)",
    )

    @field_validator("records")
    @classmethod
    def _validate_records(cls, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for index, record in enumerate(records):
            try:
                VideoFeatures.model_validate(record)
            except ValidationError as exc:
                problems = "; ".join(
                    f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
                )
                raise ValueError(f"records[{index}]: {problems}") from exc
        return records


class PredictionItem(BaseModel):
    features: dict[str, Any]
    probability: float = Field(ge=0, le=1)
    viral_flag: int = Field(description="1 — прогноз «станет виральным»")
    recommendation: str = Field(description="boost / watch / skip")


class PredictResponse(BaseModel):
    model_version_id: int
    model_name: str
    predictions: list[PredictionItem]


class VideoPrediction(BaseModel):
    video_id: int
    model_version_id: int
    probability: float
    viral_flag: int
    recommendation: str


class CsvPredictionResponse(BaseModel):
    model_version_id: int
    roc_auc: float | None = Field(description="Есть, если в файле был viral_flag с двумя классами")
    rows_total: int
    rows_returned: int
    rows: list[dict[str, Any]]
