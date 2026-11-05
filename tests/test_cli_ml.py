from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from research_graph.cli import app

runner = CliRunner()


def test_make_sample_command(frame: pd.DataFrame, tmp_path: Path) -> None:
    src, dst = tmp_path / "full.csv", tmp_path / "sample.csv"
    frame.to_csv(src, index=False)
    result = runner.invoke(app, ["make-sample", "--csv", str(src), "--out", str(dst), "-n", "300"])
    assert result.exit_code == 0
    assert dst.exists()


def test_train_command(frame: pd.DataFrame, tmp_path: Path) -> None:
    src = tmp_path / "full.csv"
    frame.to_csv(src, index=False)
    out = tmp_path / "models"
    result = runner.invoke(
        app, ["train", "--csv", str(src), "--out-dir", str(out), "--k-features", "10"]
    )
    assert result.exit_code == 0, result.output
    assert (out / "model.pkl").exists()
    assert "ROC-AUC" in result.stdout


def test_train_command_fails_without_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["train", "--csv", str(tmp_path / "missing.csv")])
    assert result.exit_code != 0
