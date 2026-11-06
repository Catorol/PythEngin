"""ETL: извлечение, валидация и преобразование (без обращения к БД)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from research_graph.ml.features import FEATURES, ID_COLUMNS, TARGET
from research_graph.ml.preprocessing import clean_features

# Флаги-«хуки» в датасете -> справочник hooks.
HOOK_FLAGS: dict[str, str] = {
    "hook_problem_statement_flag": "problem_statement",
    "hook_discount_hook_flag": "discount_hook",
    "hook_shock_hook_flag": "shock_hook",
    "hook_question_hook_flag": "question_hook",
    "hook_demo_hook_flag": "demo_hook",
    "hook_before_after_hook_flag": "before_after_hook",
    "hook_social_proof_hook_flag": "social_proof_hook",
    "hook_story_hook_flag": "story_hook",
    "hook_trend_hook_flag": "trend_hook",
    "hook_product_reveal_flag": "product_reveal",
}

ID_FIELDS = ("video_id", "creator_id", "product_id")


@dataclass
class LoadRows:
    hooks: list[dict[str, Any]]
    creators: list[dict[str, Any]]
    products: list[dict[str, Any]]
    videos: list[dict[str, Any]]


def extract(path: Path, limit: int | None = None) -> pd.DataFrame:
    """Читает CSV (только нужные столбцы) и проверяет, что все они на месте."""
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    wanted = set(FEATURES) | set(ID_COLUMNS) | {TARGET}
    df = pd.read_csv(path, usecols=lambda c: c in wanted, nrows=limit)
    missing = sorted(wanted - set(df.columns))
    if missing:
        raise ValueError(f"В CSV не хватает столбцов: {', '.join(missing)}")
    return df


def _num(d: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(d[col], errors="coerce")


def _invalid_numeric(d: pd.DataFrame) -> pd.Series:
    rating = _num(d, "product_rating")
    reviews = _num(d, "product_review_count")
    return (
        _num(d, "creator_followers").isna()
        | (_num(d, "creator_followers") < 0)
        | _num(d, "creator_engagement_rate").isna()
        | (_num(d, "creator_engagement_rate") < 0)
        | _num(d, "product_price").isna()
        | (_num(d, "product_price") < 0)
        | (rating.notna() & ~rating.between(0, 5))
        | (reviews.notna() & (reviews < 0))
        | _num(d, "video_length_seconds").isna()
        | (_num(d, "video_length_seconds") <= 0)
    )


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, Counter[str]]:
    """Отбрасывает некорректные строки. Возвращает чистую таблицу и причины отказов."""
    rejected: Counter[str] = Counter()
    data = df.copy()
    for col in ID_FIELDS:
        data[col] = data[col].astype("string").str.strip().replace("", pd.NA)
    data["published_at"] = pd.to_datetime(data["date"], errors="coerce")

    checks: list[tuple[str, Callable[[pd.DataFrame], pd.Series]]] = [
        ("missing_id", lambda d: d[list(ID_FIELDS)].isna().any(axis=1)),
        ("duplicate_video_id", lambda d: d["video_id"].duplicated()),
        ("invalid_date", lambda d: d["published_at"].isna()),
        ("invalid_viral_flag", lambda d: ~_num(d, TARGET).isin([0, 1])),
        ("invalid_numeric", _invalid_numeric),
    ]
    for reason, is_bad in checks:
        bad = is_bad(data)
        if bad.any():
            rejected[reason] += int(bad.sum())
            data = data.loc[~bad]
    return data.reset_index(drop=True), rejected


def _clean_value(value: Any) -> Any:
    return None if pd.isna(value) else value


def build_rows(df: pd.DataFrame) -> LoadRows:
    """Преобразует чистую таблицу в строки для таблиц creators/products/videos/hooks."""
    df = df.reset_index(drop=True)
    feat = clean_features(df)
    records = feat.to_dict("records")

    creators: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    videos: list[dict[str, Any]] = []
    seen_creators: set[str] = set()
    seen_products: set[str] = set()

    for i, rec in enumerate(records):
        creator_ext = str(df.at[i, "creator_id"])
        product_ext = str(df.at[i, "product_id"])
        if creator_ext not in seen_creators:
            seen_creators.add(creator_ext)
            creators.append(
                {
                    "external_id": creator_ext,
                    "tier": rec["creator_tier"],
                    "category": rec["creator_category"],
                    "country": rec["creator_country"],
                    "followers": int(rec["creator_followers"]),
                    "engagement_rate": float(rec["creator_engagement_rate"]),
                }
            )
        if product_ext not in seen_products:
            seen_products.add(product_ext)
            rating = _clean_value(rec["product_rating"])
            reviews = _clean_value(rec["product_review_count"])
            products.append(
                {
                    "external_id": product_ext,
                    "category": rec["product_category"],
                    "subcategory": rec["product_subcategory"],
                    "brand_type": rec["brand_type"],
                    "price": float(rec["product_price"]),
                    "rating": None if rating is None else float(rating),
                    "review_count": 0 if reviews is None else int(reviews),
                }
            )
        videos.append(
            {
                "external_id": str(df.at[i, "video_id"]),
                "creator_ext": creator_ext,
                "product_ext": product_ext,
                "title_type": rec["video_title_type"],
                "video_format": rec["video_format"],
                "length_seconds": int(rec["video_length_seconds"]),
                "published_at": pd.Timestamp(df.at[i, "published_at"]).date(),
                "status": "published",
                "viral_flag": int(df.at[i, TARGET]),
                "features": {k: _clean_value(v) for k, v in rec.items()},
                "hook_codes": [code for flag, code in HOOK_FLAGS.items() if rec[flag] == 1],
            }
        )

    hooks = [
        {"code": code, "title": code.replace("_", " ").capitalize()} for code in HOOK_FLAGS.values()
    ]
    return LoadRows(hooks=hooks, creators=creators, products=products, videos=videos)
