import pytest

from research_graph.services.recommendation import recommend


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.0, "skip"),
        (0.149, "skip"),
        (0.15, "watch"),
        (0.249, "watch"),
        (0.25, "boost"),
        (1.0, "boost"),
    ],
)
def test_recommend_thresholds(probability: float, expected: str) -> None:
    assert recommend(probability) == expected


@pytest.mark.parametrize("probability", [-0.1, 1.1])
def test_recommend_rejects_invalid_probability(probability: float) -> None:
    with pytest.raises(ValueError):
        recommend(probability)
