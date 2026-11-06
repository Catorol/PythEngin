"""Бизнес-правило: рекомендация по бюджету на основе вероятности виральности."""

# Доля виральных видео в данных около 12,7%, поэтому пороги заданы
# относительно неё: boost ~ в 2 раза выше базовой доли, watch ~ немного выше.
BOOST_THRESHOLD = 0.25
WATCH_THRESHOLD = 0.15


def recommend(probability: float) -> str:
    """boost — усилить бюджет, watch — понаблюдать, skip — не вкладываться."""
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    if probability >= BOOST_THRESHOLD:
        return "boost"
    if probability >= WATCH_THRESHOLD:
        return "watch"
    return "skip"
