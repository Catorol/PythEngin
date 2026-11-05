"""Обучение и сравнение моделей (признаки до публикации)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from research_graph.ml.features import FEATURES, ID_COLUMNS, LEAKAGE_COLUMNS, TARGET
from research_graph.ml.preprocessing import build_pipeline, clean_dataset

log = logging.getLogger(__name__)

MODEL_FILE = "model.pkl"
METRICS_FILE = "metrics.json"


def load_dataset(path: Path, nrows: int | None = None) -> pd.DataFrame:
    """Читает только нужные столбцы большого CSV."""
    wanted = set(FEATURES) | {TARGET} | set(ID_COLUMNS)
    return pd.read_csv(path, usecols=lambda c: c in wanted, nrows=nrows)


def make_sample(src: Path, dst: Path, n: int = 5000, seed: int = 42) -> int:
    """Делает небольшую выборку для репозитория и Docker (с сохранением доли viral_flag)."""
    df = load_dataset(src)
    frac = min(1.0, n / len(df))
    sample = df.groupby(TARGET, group_keys=False).sample(frac=frac, random_state=seed)
    sample = sample.sample(frac=1.0, random_state=seed)
    dst.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(dst, index=False)
    return len(sample)


def candidate_models(seed: int = 42) -> dict[str, Any]:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=50,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=seed,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_depth=4, random_state=seed
        ),
    }


def selected_feature_names(pipe: Pipeline) -> list[str]:
    return [str(n) for n in pipe[:-1].get_feature_names_out()]


def train_and_compare(
    df: pd.DataFrame,
    out_dir: Path,
    test_size: float = 0.2,
    seed: int = 42,
    k_features: int = 25,
) -> dict[str, Any]:
    """Обучает 3 модели, выбирает лучшую по ROC-AUC, сохраняет model.pkl и metrics.json."""
    X, y = clean_dataset(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    results: dict[str, dict[str, float]] = {}
    fitted: dict[str, Pipeline] = {}
    for name, model in candidate_models(seed).items():
        started = time.perf_counter()
        pipe = build_pipeline(model, k_features=k_features).fit(X_train, y_train)
        auc = float(roc_auc_score(y_test, pipe.predict_proba(X_test)[:, 1]))
        results[name] = {
            "roc_auc": round(auc, 4),
            "fit_seconds": round(time.perf_counter() - started, 2),
        }
        fitted[name] = pipe
        log.info("%s: ROC-AUC=%.4f", name, auc)

    best = max(results, key=lambda n: results[n]["roc_auc"])
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(fitted[best], out_dir / MODEL_FILE)
    metrics: dict[str, Any] = {
        "variant": "Признаки до публикации",
        "target": TARGET,
        "n_rows": int(len(X)),
        "positive_rate": round(float(y.mean()), 4),
        "test_size": test_size,
        "models": results,
        "best_model": best,
        "best_roc_auc": results[best]["roc_auc"],
        "k_features": k_features,
        "selected_features": selected_feature_names(fitted[best]),
        "excluded_as_leakage": LEAKAGE_COLUMNS,
    }
    (out_dir / METRICS_FILE).write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics
