from pathlib import Path

import pytest
from pydantic import ValidationError

from research_graph.config import Settings, get_settings


def test_defaults() -> None:
    settings = get_settings()
    assert settings.github_token is None
    assert settings.data_dir == Path("data")
    assert settings.log_level == "INFO"
    assert settings.request_timeout == 30.0
    assert settings.max_concurrency == 8


def test_settings_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("RG_MAX_CONCURRENCY", "16")
    monkeypatch.setenv("RG_REQUEST_TIMEOUT", "5.5")
    monkeypatch.setenv("RG_GITHUB_TOKEN", "ghp_abc")
    settings = Settings()
    assert settings.log_level == "DEBUG"
    assert settings.max_concurrency == 16
    assert settings.request_timeout == 5.5
    assert settings.github_token == "ghp_abc"


def test_log_level_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_LOG_LEVEL", "debug")
    assert Settings().log_level == "DEBUG"


def test_rejects_unknown_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_LOG_LEVEL", "LOUD")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["0", "-1", "65"])
def test_rejects_invalid_concurrency(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RG_MAX_CONCURRENCY", value)
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("value", ["0", "-3", "301"])
def test_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("RG_REQUEST_TIMEOUT", value)
    with pytest.raises(ValidationError):
        Settings()


def test_ensure_data_dir_creates_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "a" / "b"
    monkeypatch.setenv("RG_DATA_DIR", str(target))
    settings = Settings()
    assert not target.exists()
    result = settings.ensure_data_dir()
    assert result == target
    assert target.is_dir()
