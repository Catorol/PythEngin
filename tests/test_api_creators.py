from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

Factory = Callable[..., dict[str, Any]]


def test_create_and_get_creator(client: TestClient, make_creator: Factory) -> None:
    created = make_creator("CRT_1")
    response = client.get(f"/creators/{created['id']}")
    assert response.status_code == 200
    assert response.json()["external_id"] == "CRT_1"


def test_duplicate_creator_returns_409_in_common_error_format(
    client: TestClient, make_creator: Factory
) -> None:
    make_creator("CRT_1")
    response = client.post(
        "/creators",
        json={
            "external_id": "CRT_1",
            "tier": "Micro",
            "category": "Beauty",
            "country": "US",
            "followers": 10,
            "engagement_rate": 1.0,
        },
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "conflict"
    assert "CRT_1" in error["message"]


def test_validation_error_has_common_format(client: TestClient) -> None:
    response = client.post(
        "/creators",
        json={
            "external_id": "x",
            "tier": "Micro",
            "category": "Beauty",
            "country": "US",
            "followers": -5,
            "engagement_rate": 1.0,
        },
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "followers"


def test_missing_creator_returns_404(client: TestClient) -> None:
    response = client.get("/creators/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unknown_route_uses_common_error_format(client: TestClient) -> None:
    response = client.get("/no-such-route")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_list_pagination_filter_and_sort(client: TestClient, make_creator: Factory) -> None:
    for i, (tier, followers) in enumerate(
        [("Micro", 100), ("Macro", 500), ("Micro", 300), ("Mega", 900), ("Micro", 200)]
    ):
        make_creator(f"c{i}", tier=tier, followers=followers)

    page = client.get("/creators", params={"sort_by": "followers", "order": "desc", "size": 2})
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 5
    assert [c["followers"] for c in body["items"]] == [900, 500]

    second = client.get(
        "/creators", params={"sort_by": "followers", "order": "desc", "size": 2, "page": 2}
    )
    assert [c["followers"] for c in second.json()["items"]] == [300, 200]

    micro = client.get("/creators", params={"tier": "Micro"}).json()
    assert micro["total"] == 3


def test_invalid_sort_field_returns_422(client: TestClient) -> None:
    response = client.get("/creators", params={"sort_by": "password"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_partial_update(client: TestClient, make_creator: Factory) -> None:
    created = make_creator("c1")
    response = client.patch(f"/creators/{created['id']}", json={"followers": 777})
    assert response.status_code == 200
    assert response.json()["followers"] == 777
    assert response.json()["tier"] == "Micro"


def test_delete_creator(client: TestClient, make_creator: Factory) -> None:
    created = make_creator("c1")
    assert client.delete(f"/creators/{created['id']}").status_code == 204
    assert client.get(f"/creators/{created['id']}").status_code == 404


def test_cannot_delete_creator_with_videos(client: TestClient, make_video: Factory) -> None:
    video = make_video("v1")
    response = client.delete(f"/creators/{video['creator_id']}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
