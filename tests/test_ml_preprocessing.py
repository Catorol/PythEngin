import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from research_graph.ml.features import FEATURES, LEAKAGE_COLUMNS, TARGET
from research_graph.ml.preprocessing import (
    QuantileClipper,
    build_pipeline,
    clean_dataset,
    clean_features,
    validate_columns,
)


def test_features_have_no_leakage_or_duplicates() -> None:
    assert not set(FEATURES) & set(LEAKAGE_COLUMNS)
    assert TARGET not in FEATURES
    assert len(FEATURES) == len(set(FEATURES))


def test_validate_columns_reports_missing(frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="creator_followers"):
        validate_columns(frame.drop(columns=["creator_followers"]))


def test_clean_features_fixes_types(frame: pd.DataFrame) -> None:
    dirty = frame.copy()
    dirty["creator_followers"] = dirty["creator_followers"].astype(object)
    dirty.loc[0, "creator_followers"] = "abc"
    dirty.loc[1, "product_price"] = np.inf
    dirty.loc[2, "season"] = None
    cleaned = clean_features(dirty)
    assert np.isnan(cleaned.loc[0, "creator_followers"])
    assert np.isnan(cleaned.loc[1, "product_price"])
    assert cleaned.loc[2, "season"] == "unknown"


def test_clean_dataset_drops_duplicates_and_bad_targets(frame: pd.DataFrame) -> None:
    bad_nan = frame.iloc[[0]].copy()
    bad_nan[TARGET] = np.nan
    bad_value = frame.iloc[[1]].copy()
    bad_value[TARGET] = 2
    dirty = pd.concat([frame, frame.iloc[[3]], bad_nan, bad_value], ignore_index=True)
    X, y = clean_dataset(dirty)
    assert len(X) == len(y) == len(frame)
    assert set(y.unique()) <= {0, 1}


def test_quantile_clipper_uses_train_quantiles() -> None:
    train = np.append(np.arange(100, dtype=float), 1e6).reshape(-1, 1)
    clipper = QuantileClipper().fit(train)
    assert clipper.transform(train).max() < 1e6
    assert clipper.transform(np.array([[1e9]]))[0, 0] == pytest.approx(clipper.high_[0])


def test_pipeline_keeps_k_features(frame: pd.DataFrame) -> None:
    X, y = clean_dataset(frame)
    pipe = build_pipeline(LogisticRegression(max_iter=500), k_features=10).fit(X, y)
    assert len(pipe[:-1].get_feature_names_out()) == 10
    assert pipe.predict_proba(X).shape == (len(X), 2)
