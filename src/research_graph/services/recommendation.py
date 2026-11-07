"""Бизнес-правило: рекомендация по бюджету на основе вероятности виральности."""

# Базовая доля виральных видео в данных около 13%. Пороги подобраны под
# вероятности базовой модели (она почти не выдаёт значений выше 0,26):
# при p >= 0.20 доля виральных около 23% (в 1,8 раза выше базовой),
# при p >= 0.15 около 20%.
BOOST_THRESHOLD = 0.20
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


def predicted_flag(probability: float) -> int:
    """Прогноз «виральное / нет»: 1, если рекомендация boost."""
    return 1 if recommend(probability) == "boost" else 0
