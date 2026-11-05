import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from research_graph.ml.features import (
    CATEGORICAL_FEATURES,
    FLAG_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
)


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
