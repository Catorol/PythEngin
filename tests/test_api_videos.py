from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from research_graph.models import Hook, ModelVersion, Prediction

Factory = Callable[..., dict[str, Any]]


def add_hooks(session_factory: sessionmaker[Session], *codes: str) -> None:
    with session_factory() as session:
        session.add_all([Hook(code=c, title=c.title()) for c in codes])
        session.commit()


def add_prediction(
    session_factory: sessionmaker[Session], video_id: int, probability: float, recommendation: str
) -> None:
    with session_factory() as session:
        version = ModelVersion(name="m", filename=f"m-{video_id}-{probability}.pkl")
        session.add(version)
        session.commit()
        session.add(
            Prediction(
                video_id=video_id,
                model_version_id=version.id,
                probability=probability,
                predicted_flag=int(probability >= 0.5),
                recommendation=recommendation,
            )
        )
        session.commit()


def test_create_video_with_hooks_starts_as_draft(
    client: TestClient, make_video: Factory, session_factory: sessionmaker[Session]
) -> None:
    add_hooks(session_factory, "demo_hook", "story_hook")
    video = make_video("v1", hook_codes=["demo_hook", "story_hook"], features={"a": 1})
    assert video["status"] == "draft"
    assert sorted(h["code"] for h in video["hooks"]) == ["demo_hook", "story_hook"]
    assert video["features"] == {"a": 1}


def test_create_video_with_unknown_creator_returns_404(
    client: TestClient, make_product: Factory
) -> None:
    product = make_product("p1")
    response = client.post(
        "/videos",
        json={
            "external_id": "v1",
            "creator_id": 999,
            "product_id": product["id"],
            "length_seconds": 30,
        },
    )
    assert response.status_code == 404


def test_create_video_with_unknown_hook_returns_400(
    client: TestClient, make_creator: Factory, make_product: Factory
) -> None:
    response = client.post(
        "/videos",
        json={
            "external_id": "v1",
            "creator_id": make_creator("c1")["id"],
            "product_id": make_product("p1")["id"],
            "length_seconds": 30,
            "hook_codes": ["no_such_hook"],
        },
    )
    assert response.status_code == 400
    assert "no_such_hook" in response.json()["error"]["message"]


def test_duplicate_video_returns_409(client: TestClient, make_video: Factory) -> None:
    video = make_video("v1")
    response = client.post(
        "/videos",
        json={
            "external_id": "v1",
            "creator_id": video["creator_id"],
            "product_id": video["product_id"],
            "length_seconds": 10,
        },
    )
    assert response.status_code == 409


def test_video_validation_error(client: TestClient) -> None:
    response = client.post(
        "/videos", json={"external_id": "v", "creator_id": 1, "product_id": 1, "length_seconds": 0}
    )
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "length_seconds"


def test_list_filters_and_sort(client: TestClient, make_video: Factory) -> None:
    make_video("v1", length_seconds=60, video_format="Tutorial", published_at="2025-01-10")
    make_video("v2", length_seconds=15, video_format="Review", published_at="2025-02-10")
    make_video("v3", length_seconds=45, video_format="Tutorial", published_at="2025-03-10")

    tutorials = client.get("/videos", params={"video_format": "Tutorial"}).json()
    assert tutorials["total"] == 2

    by_length = client.get("/videos", params={"sort_by": "length_seconds", "order": "desc"}).json()
    assert [v["length_seconds"] for v in by_length["items"]] == [60, 45, 15]

    period = client.get(
        "/videos", params={"published_from": "2025-02-01", "published_to": "2025-02-28"}
    ).json()
    assert [v["external_id"] for v in period["items"]] == ["v2"]

    paged = client.get("/videos", params={"size": 2, "page": 2}).json()
    assert paged["total"] == 3
    assert len(paged["items"]) == 1


def test_status_flow_draft_published_archived(client: TestClient, make_video: Factory) -> None:
    video = make_video("v1")
    published = client.patch(f"/videos/{video['id']}/status", json={"status": "published"})
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    archived = client.patch(f"/videos/{video['id']}/status", json={"status": "archived"})
    assert archived.json()["status"] == "archived"


def test_forbidden_transition_returns_409(client: TestClient, make_video: Factory) -> None:
    video = make_video("v1")
    response = client.patch(f"/videos/{video['id']}/status", json={"status": "boosted"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state_transition"


def test_boost_requires_boost_recommendation(
    client: TestClient, make_video: Factory, session_factory: sessionmaker[Session]
) -> None:
    video = make_video("v1")
    url = f"/videos/{video['id']}/status"
    assert client.patch(url, json={"status": "published"}).status_code == 200

    no_prediction = client.patch(url, json={"status": "boosted"})
    assert no_prediction.status_code == 409

    add_prediction(session_factory, video["id"], 0.1, "skip")
    weak_prediction = client.patch(url, json={"status": "boosted"})
    assert weak_prediction.status_code == 409

    add_prediction(session_factory, video["id"], 0.4, "boost")
    assert client.patch(url, json={"status": "boosted"}).json()["status"] == "boosted"


def test_update_and_delete_video(client: TestClient, make_video: Factory) -> None:
    video = make_video("v1")
    updated = client.patch(f"/videos/{video['id']}", json={"length_seconds": 99})
    assert updated.status_code == 200
    assert updated.json()["length_seconds"] == 99
    assert client.delete(f"/videos/{video['id']}").status_code == 204
    assert client.get(f"/videos/{video['id']}").status_code == 404


def test_hooks_endpoint_and_health(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    add_hooks(session_factory, "story_hook", "demo_hook")
    codes = [h["code"] for h in client.get("/hooks").json()]
    assert codes == ["demo_hook", "story_hook"]
    assert client.get("/health").json() == {"status": "ok"}
