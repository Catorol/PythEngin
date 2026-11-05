from pathlib import Path

import pytest

from research_graph.config import Settings


def test_database_and_model_defaults() -> None:
    settings = Settings()
    assert settings.database_url.startswith("postgresql")
    assert settings.model_dir == Path("models")


def test_database_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("RG_MODEL_DIR", "artifacts")
    settings = Settings()
    assert settings.database_url == "sqlite:///test.db"
    assert settings.model_dir == Path("artifacts")
