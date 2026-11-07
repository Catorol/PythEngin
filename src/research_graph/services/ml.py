"""Реестр моделей и предсказания."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_graph.api.errors import (
    BadRequestError,
    ConflictError,
    ModelNotLoadedError,
    NotFoundError,
)
from research_graph.config import get_settings
from research_graph.ml import inference
from research_graph.ml.inference import InvalidInputError, InvalidModelError
from research_graph.models import ModelVersion, Prediction
from research_graph.schemas.prediction import PredictionItem, PredictResponse, VideoPrediction
from research_graph.services.recommendation import predicted_flag, recommend
from research_graph.services.videos import get_video

log = logging.getLogger(__name__)

_PIPELINES: dict[tuple[int, str], Any] = {}


def clear_model_cache() -> None:
    _PIPELINES.clear()


def get_active_version(db: Session) -> ModelVersion:
    version = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    if version is None:
        raise ModelNotLoadedError("Модель не загружена: сначала вызовите POST /upload-model")
    return version


def get_pipeline(version: ModelVersion) -> Any:
    key = (version.id, version.filename)
    cached = _PIPELINES.get(key)
    if cached is not None:
        return cached
    path = get_settings().model_dir / version.filename
    if not path.exists():
        raise ModelNotLoadedError(f"Файл модели {version.filename} не найден на диске")
    try:
        pipeline = inference.load_pipeline_file(path)
    except InvalidModelError as exc:
        raise ModelNotLoadedError(str(exc)) from exc
    _PIPELINES[key] = pipeline
    return pipeline


def _activate(db: Session, version: ModelVersion) -> None:
    """Атомарно делает версию активной: сначала снимает флаг с остальных."""
    db.execute(
        update(ModelVersion)
        .where(ModelVersion.id != version.id, ModelVersion.is_active.is_(True))
        .values(is_active=False)
    )
    version.is_active = True
    db.flush()


def register_model(
    db: Session,
    *,
    data: bytes,
    name: str,
    metrics: dict[str, Any] | None = None,
    relative_path: str | None = None,
    activate: bool = True,
) -> ModelVersion:
    """Проверяет модель, сохраняет файл и в одной транзакции делает её активной."""
    try:
        pipeline = inference.load_pipeline_bytes(data)
    except InvalidModelError as exc:
        raise BadRequestError(str(exc)) from exc

    relative = relative_path or f"uploaded/{uuid.uuid4().hex}.pkl"
    target = get_settings().model_dir / relative
    created_file = not target.exists()
    if created_file:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    version = ModelVersion(
        name=name,
        filename=relative,
        algorithm=inference.algorithm_name(pipeline),
        roc_auc=(metrics or {}).get("best_roc_auc"),
        metrics=metrics,
        is_active=False,
    )
    try:
        db.add(version)
        db.flush()
        if activate:
            _activate(db, version)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if created_file:
            target.unlink(missing_ok=True)
        raise ConflictError("Модель с таким файлом уже зарегистрирована") from exc
    except Exception:
        db.rollback()
        if created_file:
            target.unlink(missing_ok=True)
        raise
    _PIPELINES[(version.id, version.filename)] = pipeline
    return version


def register_baseline(db: Session, path: Path) -> tuple[ModelVersion, bool]:
    """Регистрирует обученную локально модель. Повторный вызов ничего не дублирует."""
    model_dir = get_settings().model_dir
    try:
        relative: str | None = path.resolve().relative_to(model_dir.resolve()).as_posix()
    except ValueError:
        relative = None
    if relative is not None:
        existing = db.scalar(select(ModelVersion).where(ModelVersion.filename == relative))
        if existing is not None:
            return existing, False
    metrics_path = path.with_name("metrics.json")
    metrics = (
        json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else None
    )
    version = register_model(
        db, data=path.read_bytes(), name="baseline", metrics=metrics, relative_path=relative
    )
    return version, True


def list_models(db: Session) -> list[ModelVersion]:
    return list(db.scalars(select(ModelVersion).order_by(ModelVersion.id.desc())))


def activate_model(db: Session, model_id: int) -> ModelVersion:
    version = db.get(ModelVersion, model_id)
    if version is None:
        raise NotFoundError(f"Модель {model_id} не найдена")
    get_pipeline(version)  # убеждаемся, что файл читается
    try:
        _activate(db, version)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return version


def predict_records(db: Session, records: list[dict[str, Any]]) -> PredictResponse:
    version = get_active_version(db)
    pipeline = get_pipeline(version)
    probabilities = inference.predict_proba(pipeline, inference.records_to_frame(records))

    items = [
        PredictionItem(
            features=record,
            probability=round(float(p), 6),
            viral_flag=predicted_flag(float(p)),
            recommendation=recommend(float(p)),
        )
        for record, p in zip(records, probabilities, strict=True)
    ]
    db.add_all(
        Prediction(
            model_version_id=version.id,
            probability=item.probability,
            predicted_flag=item.viral_flag,
            recommendation=item.recommendation,
        )
        for item in items
    )
    db.commit()
    return PredictResponse(model_version_id=version.id, model_name=version.name, predictions=items)


def predict_video(db: Session, video_id: int) -> VideoPrediction:
    """Предсказание по сохранённым признакам видео; результат сохраняется в predictions."""
    video = get_video(db, video_id)
    version = get_active_version(db)
    pipeline = get_pipeline(version)
    probability = float(
        inference.predict_proba(pipeline, inference.records_to_frame([video.features]))[0]
    )
    prediction = Prediction(
        video_id=video.id,
        model_version_id=version.id,
        probability=round(probability, 6),
        predicted_flag=predicted_flag(probability),
        recommendation=recommend(probability),
    )
    db.add(prediction)
    db.commit()
    return VideoPrediction(
        video_id=video.id,
        model_version_id=version.id,
        probability=prediction.probability,
        viral_flag=prediction.predicted_flag,
        recommendation=prediction.recommendation or "skip",
    )


def predict_csv(db: Session, source: BinaryIO) -> tuple[ModelVersion, pd.DataFrame, float | None]:
    version = get_active_version(db)
    pipeline = get_pipeline(version)
    try:
        frame = inference.read_csv_features(source)
    except InvalidInputError as exc:
        raise BadRequestError(str(exc)) from exc
    probabilities = inference.predict_proba(pipeline, frame)
    scored, roc_auc = inference.score_dataset(frame, probabilities)
    return version, scored, roc_auc
