from importlib.metadata import version as pkg_version

import pytest
from typer.testing import CliRunner

from research_graph.cli import app, mask_token

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == pkg_version("research-graph")


def test_help_lists_both_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output
    assert "check-config" in result.output


def test_check_config_defaults() -> None:
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "log_level:        INFO" in result.stdout
    assert "github_token:     не задан" in result.stdout


def test_check_config_shows_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_MAX_CONCURRENCY", "16")
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "max_concurrency:  16" in result.stdout


def test_check_config_hides_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_GITHUB_TOKEN", "ghp_supersecretvalue")
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code == 0
    assert "ghp_supersecretvalue" not in result.stdout
    assert "ghp_****alue" in result.stdout


def test_check_config_fails_on_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_MAX_CONCURRENCY", "0")
    result = runner.invoke(app, ["check-config"])
    assert result.exit_code != 0


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (None, "не задан"),
        ("", "не задан"),
        ("short", "****"),
        ("ghp_supersecretvalue", "ghp_****alue"),
    ],
)
def test_mask_token(token: str | None, expected: str) -> None:
    assert mask_token(token) == expected
