from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Query, Response, UploadFile

from research_graph.api.deps import DbSession
from research_graph.api.errors import BadRequestError, ErrorResponse
from research_graph.schemas.model import ModelUploadResponse, ModelVersionRead
from research_graph.schemas.prediction import (
    CsvPredictionResponse,
    PredictRequest,
    PredictResponse,
    VideoPrediction,
)
from research_graph.services import ml as service

router = APIRouter(tags=["ml"])

MAX_MODEL_BYTES = 100 * 1024 * 1024
MODEL_SUFFIXES = {".pkl", ".joblib"}

NO_MODEL: dict[int | str, dict[str, Any]] = {
    409: {"model": ErrorResponse, "description": "Модель не загружена"}
}
BAD_INPUT: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Некорректный файл или данные"}
}


@router.post(
    "/upload-model",
    response_model=ModelUploadResponse,
    status_code=201,
    responses=BAD_INPUT,
    summary="Загрузить модель (pkl) и сделать её активной",
)
def upload_model(
    db: DbSession,
    file: Annotated[UploadFile, File(description="sklearn Pipeline в формате .pkl (joblib)")],
) -> ModelUploadResponse:
    """Загружайте только доверенные файлы: pkl исполняет код при чтении."""
    filename = file.filename or "model.pkl"
    if Path(filename).suffix.lower() not in MODEL_SUFFIXES:
        raise BadRequestError("Ожидается файл .pkl или .joblib")
    data = file.file.read(MAX_MODEL_BYTES + 1)
    if len(data) > MAX_MODEL_BYTES:
        raise BadRequestError("Файл модели больше 100 МБ")
    version = service.register_model(db, data=data, name=Path(filename).stem)
    return ModelUploadResponse(model=ModelVersionRead.model_validate(version))


@router.get("/models", response_model=list[ModelVersionRead], summary="Версии моделей")
def list_models(db: DbSession) -> list[ModelVersionRead]:
    return [ModelVersionRead.model_validate(m) for m in service.list_models(db)]


@router.post(
    "/models/{model_id}/activate",
    response_model=ModelVersionRead,
    responses={404: {"model": ErrorResponse}},
    summary="Сделать версию модели активной",
)
def activate_model(model_id: int, db: DbSession) -> ModelVersionRead:
    return ModelVersionRead.model_validate(service.activate_model(db, model_id))


@router.post(
    "/predict",
    response_model=PredictResponse,
    responses=NO_MODEL,
    summary="Предсказание для одной или нескольких записей",
)
def predict(data: PredictRequest, db: DbSession) -> PredictResponse:
    """Возвращает вероятность, прогноз viral_flag и рекомендацию по бюджету.
    Если модель не загружена, вернётся 409 `model_not_loaded`."""
    return service.predict_records(db, data.records)


@router.post(
    "/videos/{video_id}/predict",
    response_model=VideoPrediction,
    responses={**NO_MODEL, 404: {"model": ErrorResponse}},
    tags=["videos"],
    summary="Предсказание по сохранённому видео",
)
def predict_video(video_id: int, db: DbSession) -> VideoPrediction:
    """Берёт признаки из видео и сохраняет предсказание (нужно для перехода в boosted)."""
    return service.predict_video(db, video_id)


@router.post(
    "/predict-from-csv",
    response_model=CsvPredictionResponse,
    responses={**NO_MODEL, **BAD_INPUT},
    summary="Предсказание по CSV",
)
def predict_from_csv(
    db: DbSession,
    file: Annotated[UploadFile, File(description="CSV с признаками (можно и с viral_flag)")],
    limit: Annotated[
        int, Query(ge=1, le=100000, description="Сколько строк вернуть в JSON")
    ] = 1000,
    response_format: Annotated[Literal["json", "csv"], Query(alias="format")] = "json",
) -> CsvPredictionResponse | Response:
    """Если в CSV есть viral_flag с двумя классами, вернётся roc_auc.
    `format=csv` отдаёт весь набор файлом (ROC-AUC в заголовке X-ROC-AUC)."""
    version, scored, roc_auc = service.predict_csv(db, file.file)
    if response_format == "csv":
        headers = {
            "Content-Disposition": 'attachment; filename="predictions.csv"',
            "X-ROC-AUC": "" if roc_auc is None else str(roc_auc),
        }
        return Response(content=scored.to_csv(index=False), media_type="text/csv", headers=headers)
    head = scored.head(limit).astype(object)
    rows = head.where(head.notna(), None).to_dict("records")
    return CsvPredictionResponse(
        model_version_id=version.id,
        roc_auc=roc_auc,
        rows_total=len(scored),
        rows_returned=len(rows),
        rows=rows,
    )
