"""Загрузка модели и предсказания (без БД и веб-фреймворка)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from research_graph.ml.features import FEATURES, TARGET
from research_graph.ml.preprocessing import clean_features, validate_columns
from research_graph.services.recommendation import predicted_flag, recommend


class InvalidModelError(ValueError):
    """Файл не является подходящей моделью."""


class InvalidInputError(ValueError):
    """Входные данные нельзя использовать для предсказания."""


def records_to_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Список словарей -> таблица со всеми признаками (недостающие станут пропусками)."""
    return pd.DataFrame(records).reindex(columns=FEATURES)


def predict_proba(pipeline: Any, frame: pd.DataFrame) -> np.ndarray:
    """Вероятность класса 1 для каждой строки."""
    cleaned = clean_features(frame.reindex(columns=FEATURES))
    return np.asarray(pipeline.predict_proba(cleaned)[:, 1], dtype=float)


def smoke_test(pipeline: Any) -> None:
    """Проверяет, что модель умеет предсказывать по признакам сервиса."""
    row = pd.DataFrame([{c: None for c in FEATURES}])
    try:
        proba = pipeline.predict_proba(clean_features(row))
    except Exception as exc:
        raise InvalidModelError(f"Модель несовместима с признаками сервиса: {exc}") from exc
    if getattr(proba, "shape", None) != (1, 2):
        raise InvalidModelError("predict_proba должен возвращать вероятности двух классов")


def _validated(obj: Any) -> Any:
    if not hasattr(obj, "predict_proba"):
        raise InvalidModelError("В файле не модель: нет метода predict_proba")
    smoke_test(obj)
    return obj


def load_pipeline_bytes(data: bytes) -> Any:
    try:
        obj = joblib.load(io.BytesIO(data))
    except Exception as exc:
        raise InvalidModelError("Не удалось прочитать файл модели") from exc
    return _validated(obj)


def load_pipeline_file(path: Path) -> Any:
    try:
        obj = joblib.load(path)
    except Exception as exc:
        raise InvalidModelError(f"Не удалось прочитать файл модели {path.name}") from exc
    return _validated(obj)


def algorithm_name(pipeline: Any) -> str:
    final = pipeline.steps[-1][1] if hasattr(pipeline, "steps") else pipeline
    return type(final).__name__


def read_csv_features(source: BinaryIO | Path) -> pd.DataFrame:
    """Читает CSV целиком и проверяет, что в нём есть все признаки модели."""
    try:
        df = pd.read_csv(source)
    except Exception as exc:
        raise InvalidInputError("Не удалось прочитать CSV") from exc
    if df.empty:
        raise InvalidInputError("CSV не содержит строк")
    try:
        validate_columns(df)
    except ValueError as exc:
        raise InvalidInputError(str(exc)) from exc
    return df


def score_dataset(df: pd.DataFrame, probabilities: np.ndarray) -> tuple[pd.DataFrame, float | None]:
    """Добавляет к таблице предсказания и считает ROC-AUC, если есть viral_flag."""
    out = df.copy()
    out["predicted_probability"] = np.round(probabilities, 6)
    out["predicted_viral_flag"] = [predicted_flag(float(p)) for p in probabilities]
    out["recommendation"] = [recommend(float(p)) for p in probabilities]

    roc_auc: float | None = None
    if TARGET in df.columns:
        target = pd.to_numeric(df[TARGET], errors="coerce")
        known = target.isin([0, 1]).to_numpy()
        if known.any() and target[known].nunique() == 2:
            roc_auc = round(float(roc_auc_score(target[known], probabilities[known])), 4)
    return out, roc_auc
