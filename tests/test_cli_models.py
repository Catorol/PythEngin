import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from research_graph.cli import app
from research_graph.db import Base, create_db_engine
from research_graph.models import ModelVersion

runner = CliRunner()


def test_register_model_command_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, model_bytes: bytes
) -> None:
    url = f"sqlite:///{(tmp_path / 'cli.db').as_posix()}"
    monkeypatch.setenv("RG_DATABASE_URL", url)
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)

    model_dir = Path("models")
    model_dir.mkdir()
    (model_dir / "model.pkl").write_bytes(model_bytes)
    (model_dir / "metrics.json").write_text(json.dumps({"best_roc_auc": 0.67}), encoding="utf-8")

    first = runner.invoke(app, ["register-model", "--path", "models/model.pkl"])
    assert first.exit_code == 0, first.output
    assert "зарегистрирована и активна" in first.stdout

    second = runner.invoke(app, ["register-model", "--path", "models/model.pkl"])
    assert second.exit_code == 0
    assert "уже зарегистрирована" in second.stdout

    with Session(engine) as session:
        versions = list(session.scalars(select(ModelVersion)))
    assert len(versions) == 1
    assert versions[0].is_active is True
    assert versions[0].roc_auc == 0.67
    assert versions[0].filename == "model.pkl"
    engine.dispose()
