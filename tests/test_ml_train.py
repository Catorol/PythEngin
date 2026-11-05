import json
from pathlib import Path

import joblib
import pandas as pd

from research_graph.ml.features import TARGET
from research_graph.ml.train import (
    METRICS_FILE,
    MODEL_FILE,
    load_dataset,
    make_sample,
    train_and_compare,
)


def test_load_dataset_reads_only_needed_columns(frame: pd.DataFrame, tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    frame.assign(unused_column=1).to_csv(path, index=False)
    loaded = load_dataset(path)
    assert "unused_column" not in loaded.columns
    assert TARGET in loaded.columns


def test_make_sample_keeps_both_classes(frame: pd.DataFrame, tmp_path: Path) -> None:
    src, dst = tmp_path / "full.csv", tmp_path / "out" / "sample.csv"
    frame.to_csv(src, index=False)
    size = make_sample(src, dst, n=300)
    sample = pd.read_csv(dst)
    assert len(sample) == size
    assert 250 <= size <= 350
    assert set(sample[TARGET].unique()) == {0, 1}


def test_train_and_compare_saves_artifacts(frame: pd.DataFrame, tmp_path: Path) -> None:
    metrics = train_and_compare(frame, tmp_path / "models", k_features=10)
    assert set(metrics["models"]) == {
        "logistic_regression",
        "random_forest",
        "hist_gradient_boosting",
    }
    assert metrics["best_model"] in metrics["models"]
    assert metrics["best_roc_auc"] > 0.6
    assert len(metrics["selected_features"]) == 10

    saved = json.loads((tmp_path / "models" / METRICS_FILE).read_text(encoding="utf-8"))
    assert saved["best_model"] == metrics["best_model"]

    model = joblib.load(tmp_path / "models" / MODEL_FILE)
    proba = model.predict_proba(frame.drop(columns=[TARGET]))
    assert proba.shape == (len(frame), 2)
