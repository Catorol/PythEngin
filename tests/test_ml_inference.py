import io

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from research_graph.ml.features import FEATURES, TARGET
from research_graph.ml.inference import (
    InvalidInputError,
    InvalidModelError,
    algorithm_name,
    load_pipeline_bytes,
    predict_proba,
    read_csv_features,
    records_to_frame,
    score_dataset,
)


def test_records_to_frame_adds_missing_columns() -> None:
    frame = records_to_frame([{"creator_followers": 5}])
    assert list(frame.columns) == FEATURES
    assert frame.shape == (1, len(FEATURES))


def test_predict_proba_returns_probabilities(
    fitted_pipeline: Pipeline, frame: pd.DataFrame
) -> None:
    records = frame[FEATURES].head(3).to_dict("records")
    probabilities = predict_proba(fitted_pipeline, records_to_frame(records))
    assert probabilities.shape == (3,)
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_predict_proba_works_for_empty_record(fitted_pipeline: Pipeline) -> None:
    probabilities = predict_proba(fitted_pipeline, records_to_frame([{}]))
    assert probabilities.shape == (1,)


def test_load_pipeline_bytes_accepts_valid_model(model_bytes: bytes) -> None:
    assert algorithm_name(load_pipeline_bytes(model_bytes)) == "LogisticRegression"


def test_load_pipeline_bytes_rejects_garbage() -> None:
    with pytest.raises(InvalidModelError):
        load_pipeline_bytes(b"not a pickle")


def test_load_pipeline_bytes_rejects_object_without_predict_proba() -> None:
    buffer = io.BytesIO()
    joblib.dump({"a": 1}, buffer)
    with pytest.raises(InvalidModelError, match="predict_proba"):
        load_pipeline_bytes(buffer.getvalue())


def test_load_pipeline_bytes_rejects_incompatible_model() -> None:
    model = LogisticRegression().fit([[0, 1], [1, 0], [0, 0], [1, 1]], [0, 1, 0, 1])
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    with pytest.raises(InvalidModelError, match="несовместима"):
        load_pipeline_bytes(buffer.getvalue())


def test_read_csv_features_requires_all_columns(frame: pd.DataFrame) -> None:
    csv = frame.drop(columns=["product_price"]).to_csv(index=False).encode()
    with pytest.raises(InvalidInputError, match="product_price"):
        read_csv_features(io.BytesIO(csv))


def test_read_csv_features_rejects_empty_file(frame: pd.DataFrame) -> None:
    header_only = ",".join(frame.columns).encode() + b"\n"
    with pytest.raises(InvalidInputError, match="строк"):
        read_csv_features(io.BytesIO(header_only))


def test_score_dataset_adds_columns_and_roc_auc(frame: pd.DataFrame) -> None:
    probabilities = frame["creator_engagement_rate"].rank(pct=True).to_numpy() * 0.5
    scored, roc_auc = score_dataset(frame, probabilities)
    assert {"predicted_probability", "predicted_viral_flag", "recommendation"} <= set(
        scored.columns
    )
    assert roc_auc is not None and roc_auc > 0.7
    assert len(scored) == len(frame)


def test_score_dataset_without_target_has_no_roc_auc(frame: pd.DataFrame) -> None:
    _, roc_auc = score_dataset(frame.drop(columns=[TARGET]), np.full(len(frame), 0.1))
    assert roc_auc is None


def test_score_dataset_with_single_class_has_no_roc_auc(frame: pd.DataFrame) -> None:
    single = frame.assign(**{TARGET: 0})
    _, roc_auc = score_dataset(single, np.full(len(frame), 0.1))
    assert roc_auc is None
