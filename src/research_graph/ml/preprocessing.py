"""Очистка данных и sklearn-пайплайн предобработки."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from research_graph.ml.features import (
    CATEGORICAL_FEATURES,
    FEATURES,
    FLAG_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
)

UNKNOWN = "unknown"


class QuantileClipper(BaseEstimator, TransformerMixin):
    """Обрезает выбросы по квантилям, посчитанным только на обучающей выборке."""

    def __init__(self, lower: float = 0.01, upper: float = 0.99) -> None:
        self.lower = lower
        self.upper = upper

    def fit(self, X: Any, y: Any = None) -> QuantileClipper:
        arr = np.asarray(X, dtype=float)
        self.low_ = np.nanquantile(arr, self.lower, axis=0)
        self.high_ = np.nanquantile(arr, self.upper, axis=0)
        return self

    def transform(self, X: Any) -> Any:
        return np.clip(np.asarray(X, dtype=float), self.low_, self.high_)

    def get_feature_names_out(self, input_features: Any = None) -> Any:
        return np.asarray(input_features, dtype=object)


def validate_columns(df: pd.DataFrame, required: list[str] | None = None) -> None:
    """Бросает ValueError, если в таблице нет нужных признаков."""
    required = FEATURES if required is None else required
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Не хватает столбцов: {', '.join(missing)}")


def clean_features(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит признаки к нужным типам: числа, флаги 0/1, строки; бесконечности -> NaN."""
    validate_columns(df)
    out = df[FEATURES].copy()
    for col in NUMERIC_FEATURES + FLAG_FEATURES:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out[NUMERIC_FEATURES] = out[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan)
    for col in CATEGORICAL_FEATURES:
        out[col] = out[col].astype("object").where(out[col].notna(), UNKNOWN).astype(str)
    return out


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Чистит обучающую таблицу: дубликаты, пропуски в цели, типы. Возвращает (x, y)."""
    validate_columns(df, FEATURES + [TARGET])
    data = df.drop_duplicates().dropna(subset=[TARGET])
    y = pd.to_numeric(data[TARGET], errors="coerce")
    keep = y.isin([0, 1])
    data, y = data.loc[keep], y.loc[keep].astype(int)
    return clean_features(data).reset_index(drop=True), y.reset_index(drop=True)


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("clip", QuantileClipper()),
            ("scale", StandardScaler()),
        ]
    )
    flags = Pipeline([("impute", SimpleImputer(strategy="most_frequent"))])
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="constant", fill_value=UNKNOWN)),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", min_frequency=100, sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric, NUMERIC_FEATURES),
            ("flag", flags, FLAG_FEATURES),
            ("cat", categorical, CATEGORICAL_FEATURES),
        ],
        verbose_feature_names_out=False,
    )


def build_pipeline(model: Any, k_features: int = 25) -> Pipeline:
    """Предобработка -> отбор признаков (SelectKBest) -> модель."""
    return Pipeline(
        [
            ("prep", build_preprocessor()),
            ("variance", VarianceThreshold(0.0)),
            ("select", SelectKBest(f_classif, k=k_features)),
            ("model", model),
        ]
    )
