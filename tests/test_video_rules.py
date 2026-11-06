import pytest

from research_graph.api.errors import InvalidStateTransitionError
from research_graph.services.videos import ALLOWED_TRANSITIONS, check_transition


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("draft", "published"),
        ("draft", "archived"),
        ("published", "boosted"),
        ("boosted", "archived"),
    ],
)
def test_allowed_transitions(current: str, new: str) -> None:
    check_transition(current, new)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        ("draft", "boosted"),
        ("published", "draft"),
        ("archived", "published"),
        ("boosted", "published"),
    ],
)
def test_forbidden_transitions(current: str, new: str) -> None:
    with pytest.raises(InvalidStateTransitionError):
        check_transition(current, new)


def test_archived_is_terminal() -> None:
    assert ALLOWED_TRANSITIONS["archived"] == set()
