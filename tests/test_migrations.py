from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
APP_TABLES = {
    "creators",
    "products",
    "videos",
    "hooks",
    "video_hooks",
    "model_versions",
    "predictions",
}


def test_migration_upgrade_and_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("RG_DATABASE_URL", url)
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))

    command.upgrade(config, "head")
    engine = create_engine(url)
    assert APP_TABLES <= set(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert not APP_TABLES & set(inspect(engine).get_table_names())
    engine.dispose()
