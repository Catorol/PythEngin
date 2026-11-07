import pytest

from research_graph.services.recommendation import predicted_flag, recommend


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.0, "skip"),
        (0.149, "skip"),
        (0.15, "watch"),
        (0.199, "watch"),
        (0.2, "boost"),
        (1.0, "boost"),
    ],
)
def test_recommend_thresholds(probability: float, expected: str) -> None:
    assert recommend(probability) == expected


@pytest.mark.parametrize("probability", [-0.1, 1.1])
def test_recommend_rejects_invalid_probability(probability: float) -> None:
    with pytest.raises(ValueError):
        recommend(probability)


def test_predicted_flag_matches_boost() -> None:
    assert predicted_flag(0.2) == 1
    assert predicted_flag(0.19) == 0
