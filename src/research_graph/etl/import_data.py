"""ETL: импорт видео из CSV в БД (идемпотентно).

Запуск:
    python -m research_graph.etl.import_data --source data/sample/tiktok_sample.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import Session, sessionmaker

from research_graph.config import get_settings
from research_graph.db import create_db_engine, create_session_factory
from research_graph.etl.transform import LoadRows, build_rows, extract, validate
from research_graph.logging_setup import setup_logging
from research_graph.models import Creator, Hook, Product, Video
from research_graph.models.video import video_hooks

log = logging.getLogger(__name__)

BATCH_SIZE = 1000


@dataclass
class EtlReport:
    read: int = 0
    rejected: Counter[str] = field(default_factory=Counter)
    creators_added: int = 0
    products_added: int = 0
    videos_added: int = 0
    videos_existing: int = 0
    hook_links_added: int = 0

    @property
    def rejected_total(self) -> int:
        return sum(self.rejected.values())

    def summary(self) -> str:
        reasons = ", ".join(f"{k}={v}" for k, v in sorted(self.rejected.items())) or "нет"
        return (
            f"прочитано={self.read}, отклонено={self.rejected_total} ({reasons}), "
            f"добавлено: креаторов={self.creators_added}, товаров={self.products_added}, "
            f"видео={self.videos_added}, связей с хуками={self.hook_links_added}; "
            f"видео уже было в БД={self.videos_existing}"
        )


def _chunks(rows: list[dict[str, Any]], size: int = BATCH_SIZE) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _insert_new(session: Session, model: Any, rows: list[dict[str, Any]]) -> int:
    """Вставляет только те строки, которых ещё нет (по external_id)."""
    existing: set[str] = set(session.scalars(select(model.external_id)))
    new_rows = [r for r in rows if r["external_id"] not in existing]
    for chunk in _chunks(new_rows):
        session.execute(insert(model), chunk)
    return len(new_rows)


def _ensure_hooks(session: Session, hooks: list[dict[str, Any]]) -> dict[str, int]:
    existing = set(session.scalars(select(Hook.code)))
    missing = [h for h in hooks if h["code"] not in existing]
    if missing:
        session.execute(insert(Hook), missing)
    return {code: hook_id for hook_id, code in session.execute(select(Hook.id, Hook.code))}


def load(session: Session, rows: LoadRows, report: EtlReport) -> None:
    """Загрузка в БД одной транзакцией; повторный запуск не создаёт дубликатов."""
    try:
        hook_ids = _ensure_hooks(session, rows.hooks)
        report.creators_added = _insert_new(session, Creator, rows.creators)
        report.products_added = _insert_new(session, Product, rows.products)
        creator_ids = {
            ext: pk for pk, ext in session.execute(select(Creator.id, Creator.external_id))
        }
        product_ids = {
            ext: pk for pk, ext in session.execute(select(Product.id, Product.external_id))
        }

        existing = set(session.scalars(select(Video.external_id)))
        new_videos = [v for v in rows.videos if v["external_id"] not in existing]
        report.videos_existing = len(rows.videos) - len(new_videos)
        video_rows = [
            {
                "external_id": v["external_id"],
                "creator_id": creator_ids[v["creator_ext"]],
                "product_id": product_ids[v["product_ext"]],
                "title_type": v["title_type"],
                "video_format": v["video_format"],
                "length_seconds": v["length_seconds"],
                "published_at": v["published_at"],
                "status": v["status"],
                "viral_flag": v["viral_flag"],
                "features": v["features"],
            }
            for v in new_videos
        ]
        for chunk in _chunks(video_rows):
            session.execute(insert(Video), chunk)
        report.videos_added = len(video_rows)

        video_ids = {ext: pk for pk, ext in session.execute(select(Video.id, Video.external_id))}
        links = [
            {"video_id": video_ids[v["external_id"]], "hook_id": hook_ids[code]}
            for v in new_videos
            for code in v["hook_codes"]
        ]
        for chunk in _chunks(links):
            session.execute(insert(video_hooks), chunk)
        report.hook_links_added = len(links)
        session.commit()
    except Exception:
        session.rollback()
        raise


def run_etl(
    source: Path, session_factory: sessionmaker[Session], limit: int | None = None
) -> EtlReport:
    df = extract(source, limit)
    report = EtlReport(read=len(df))
    clean, report.rejected = validate(df)
    rows = build_rows(clean)
    with session_factory() as session:
        load(session, rows, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Импорт видео TikTok Shop из CSV в БД")
    parser.add_argument("--source", type=Path, required=True, help="Путь к CSV")
    parser.add_argument("--limit", type=int, default=None, help="Прочитать только N строк")
    args = parser.parse_args(argv)

    settings = get_settings()
    setup_logging(settings.log_level)
    try:
        engine = create_db_engine(settings.database_url)
        report = run_etl(args.source, create_session_factory(engine), args.limit)
    except (FileNotFoundError, ValueError) as exc:
        log.error("ETL остановлен: %s", exc)
        return 1
    log.info("ETL завершён: %s", report.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
