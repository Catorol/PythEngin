from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from research_graph.db import Base, create_db_engine
from research_graph.etl.import_data import main, run_etl
from research_graph.etl.transform import HOOK_FLAGS, build_rows, extract, validate
from research_graph.ml.features import TARGET
from research_graph.models import Creator, Hook, Product, Video
from research_graph.models.video import video_hooks


@pytest.fixture
def etl_frame(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    n = len(df)
    df["product_rating"] = 4.5
    df["video_id"] = [f"VID_{i}" for i in range(n)]
    df["creator_id"] = [f"CRT_{i % 20}" for i in range(n)]
    df["product_id"] = [f"PROD_{i}" for i in range(n)]
    df["date"] = "2025-10-01"
    return df


def count(session: Session, model: object) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0  # type: ignore[arg-type]


def test_extract_fails_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nope.csv")


def test_extract_fails_when_columns_missing(etl_frame: pd.DataFrame, tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    etl_frame.drop(columns=["product_price"]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="product_price"):
        extract(path)


def test_validate_rejects_bad_rows_with_reasons(etl_frame: pd.DataFrame) -> None:
    bad = etl_frame.copy()
    bad.loc[0, "video_id"] = None
    bad.loc[1, "video_id"] = bad.loc[2, "video_id"]
    bad.loc[3, "date"] = "not-a-date"
    bad.loc[4, TARGET] = 5
    bad.loc[5, "product_price"] = -1
    clean, rejected = validate(bad)
    assert dict(rejected) == {
        "missing_id": 1,
        "duplicate_video_id": 1,
        "invalid_date": 1,
        "invalid_viral_flag": 1,
        "invalid_numeric": 1,
    }
    assert len(clean) == len(etl_frame) - 5


def test_build_rows_dedupes_creators_and_maps_hooks(etl_frame: pd.DataFrame) -> None:
    df = etl_frame.copy()
    for flag in HOOK_FLAGS:
        df[flag] = 0
    df.loc[0, "hook_demo_hook_flag"] = 1
    clean, _ = validate(df)
    rows = build_rows(clean)
    assert len(rows.creators) == 20
    assert len(rows.videos) == len(df)
    assert len(rows.hooks) == len(HOOK_FLAGS)
    assert rows.videos[0]["hook_codes"] == ["demo_hook"]
    assert rows.videos[1]["hook_codes"] == []


def test_load_is_idempotent(
    etl_frame: pd.DataFrame, tmp_path: Path, session_factory: sessionmaker[Session]
) -> None:
    source = tmp_path / "data.csv"
    etl_frame.to_csv(source, index=False)

    first = run_etl(source, session_factory)
    assert first.videos_added == len(etl_frame)
    assert first.creators_added == 20

    second = run_etl(source, session_factory)
    assert second.videos_added == 0
    assert second.creators_added == 0
    assert second.videos_existing == len(etl_frame)

    with session_factory() as session:
        assert count(session, Video) == len(etl_frame)
        assert count(session, Creator) == 20
        assert count(session, Product) == len(etl_frame)
        assert count(session, Hook) == len(HOOK_FLAGS)
        assert count(session, video_hooks) == first.hook_links_added


def test_main_imports_csv_and_returns_zero(
    etl_frame: pd.DataFrame, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{(tmp_path / 'etl.db').as_posix()}"
    monkeypatch.setenv("RG_DATABASE_URL", url)
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    source = tmp_path / "data.csv"
    etl_frame.to_csv(source, index=False)

    assert main(["--source", str(source), "--limit", "100"]) == 0
    with Session(engine) as session:
        assert count(session, Video) == 100
    engine.dispose()


def test_main_returns_one_for_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RG_DATABASE_URL", f"sqlite:///{(tmp_path / 'x.db').as_posix()}")
    assert main(["--source", str(tmp_path / "missing.csv")]) == 1
