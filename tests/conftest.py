import io
import logging
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sqlalchemy.orm import Session, sessionmaker

import research_graph.models  # noqa: F401  (регистрирует таблицы в metadata)
from research_graph.api.deps import get_db
from research_graph.db import Base, create_db_engine, create_session_factory
from research_graph.main import create_app
from research_graph.ml.features import (
    CATEGORICAL_FEATURES,
    FLAG_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
)
from research_graph.ml.preprocessing import build_pipeline, clean_dataset
from research_graph.services.ml import clear_model_cache


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in list(os.environ):
        if key.startswith("RG_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    old_handlers = root.handlers[:]
    old_level = root.level
    yield
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    for handler in old_handlers:
        root.addHandler(handler)
    root.setLevel(old_level)
    for name in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.NOTSET)


@pytest.fixture(autouse=True)
def reset_model_cache() -> Iterator[None]:
    clear_model_cache()
    yield
    clear_model_cache()


@pytest.fixture
def frame() -> pd.DataFrame:
    """Синтетическая таблица со всеми признаками и целью viral_flag (сигнал в engagement_rate)."""
    rng = np.random.default_rng(0)
    n = 800
    data: dict[str, Any] = {}
    for col in NUMERIC_FEATURES:
        data[col] = rng.normal(50, 10, n)
    for col in FLAG_FEATURES:
        data[col] = rng.integers(0, 2, n)
    for col in CATEGORICAL_FEATURES:
        data[col] = rng.choice(["a", "b", "c"], n)
    df = pd.DataFrame(data)
    score = df["creator_engagement_rate"] + rng.normal(0, 5, n)
    df[TARGET] = (score > score.quantile(0.8)).astype(int)
    return df


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    Base.metadata.create_all(engine)
    yield create_session_factory(engine)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()

    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_creator(client: TestClient) -> Callable[..., dict[str, Any]]:
    def factory(external_id: str = "c1", **overrides: Any) -> dict[str, Any]:
        payload = {
            "external_id": external_id,
            "tier": "Micro",
            "category": "Beauty",
            "country": "US",
            "followers": 1000,
            "engagement_rate": 5.0,
            **overrides,
        }
        response = client.post("/creators", json=payload)
        assert response.status_code == 201, response.text
        return dict(response.json())

    return factory


@pytest.fixture
def make_product(client: TestClient) -> Callable[..., dict[str, Any]]:
    def factory(external_id: str = "p1", **overrides: Any) -> dict[str, Any]:
        payload = {"external_id": external_id, "category": "Beauty", "price": 19.9, **overrides}
        response = client.post("/products", json=payload)
        assert response.status_code == 201, response.text
        return dict(response.json())

    return factory


@pytest.fixture
def make_video(
    client: TestClient,
    make_creator: Callable[..., dict[str, Any]],
    make_product: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def factory(external_id: str = "v1", **overrides: Any) -> dict[str, Any]:
        if "creator_id" not in overrides:
            overrides["creator_id"] = make_creator(f"c-{external_id}")["id"]
        if "product_id" not in overrides:
            overrides["product_id"] = make_product(f"p-{external_id}")["id"]
        payload = {"external_id": external_id, "length_seconds": 30, **overrides}
        response = client.post("/videos", json=payload)
        assert response.status_code == 201, response.text
        return dict(response.json())

    return factory


@pytest.fixture
def fitted_pipeline(frame: pd.DataFrame) -> Pipeline:
    X, y = clean_dataset(frame)
    return build_pipeline(LogisticRegression(max_iter=500), k_features=10).fit(X, y)


@pytest.fixture
def model_bytes(fitted_pipeline: Pipeline) -> bytes:
    buffer = io.BytesIO()
    joblib.dump(fitted_pipeline, buffer)
    return buffer.getvalue()
