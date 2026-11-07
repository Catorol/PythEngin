from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from research_graph.models import Creator, Hook, Product, Video


@pytest.fixture
def seeded(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        demo, story = Hook(code="demo_hook", title="Demo"), Hook(code="story_hook", title="Story")
        c0, c1 = (
            Creator(
                external_id=f"c{i}",
                tier="Micro",
                category="Beauty",
                country="US",
                followers=100 * (i + 1),
                engagement_rate=1.0,
            )
            for i in range(2)
        )
        product = Product(external_id="p", category="Beauty", price=1.0)
        session.add_all([demo, story, c0, c1, product])
        session.flush()

        specs = [
            (c0, date(2025, 1, 5), 1, [demo]),
            (c0, date(2025, 1, 20), 0, [demo, story]),
            (c0, date(2025, 2, 10), 1, [story]),
            (c1, date(2025, 2, 11), 0, [demo]),
            (c1, date(2025, 2, 12), 0, []),
            (c1, date(2025, 3, 1), None, [demo]),  # без viral_flag: в статистику не попадает
        ]
        for i, (creator, published, viral, hooks) in enumerate(specs):
            video = Video(
                external_id=f"v{i}",
                creator_id=creator.id,
                product_id=product.id,
                length_seconds=30,
                published_at=published,
                viral_flag=viral,
                features={},
            )
            video.hooks = hooks
            session.add(video)
        session.commit()


def test_virality_by_hook(client: TestClient, seeded: None) -> None:
    response = client.get("/analytics/virality-by-hook")
    assert response.status_code == 200
    stats = {s["hook_code"]: s for s in response.json()}
    assert stats["story_hook"]["videos"] == 2
    assert stats["story_hook"]["viral_rate"] == 0.5
    assert stats["demo_hook"]["videos"] == 3
    assert stats["demo_hook"]["viral_rate"] == pytest.approx(0.3333, abs=1e-4)
    assert [s["hook_code"] for s in response.json()] == ["story_hook", "demo_hook"]


def test_virality_by_hook_min_videos_filter(client: TestClient, seeded: None) -> None:
    response = client.get("/analytics/virality-by-hook", params={"min_videos": 3})
    assert [s["hook_code"] for s in response.json()] == ["demo_hook"]


def test_top_creators(client: TestClient, seeded: None) -> None:
    response = client.get("/analytics/top-creators", params={"min_videos": 1})
    assert response.status_code == 200
    body = response.json()
    assert [c["external_id"] for c in body] == ["c0", "c1"]
    assert body[0]["videos"] == 3
    assert body[0]["viral_rate"] == pytest.approx(0.6667, abs=1e-4)
    assert body[1]["viral_rate"] == 0.0

    strict = client.get("/analytics/top-creators", params={"min_videos": 3, "limit": 1}).json()
    assert [c["external_id"] for c in strict] == ["c0"]


def test_viral_trend_by_month(client: TestClient, seeded: None) -> None:
    response = client.get("/analytics/viral-trend")
    assert response.status_code == 200
    assert response.json() == [
        {"period": "2025-01", "videos": 2, "viral_videos": 1, "viral_rate": 0.5},
        {"period": "2025-02", "videos": 3, "viral_videos": 1, "viral_rate": 0.3333},
    ]


def test_viral_trend_date_filter(client: TestClient, seeded: None) -> None:
    response = client.get("/analytics/viral-trend", params={"published_from": "2025-02-01"})
    assert [p["period"] for p in response.json()] == ["2025-02"]


def test_analytics_validates_params(client: TestClient) -> None:
    assert client.get("/analytics/top-creators", params={"limit": 0}).status_code == 422
    assert client.get("/analytics/viral-trend", params={"published_from": "bad"}).status_code == 422
