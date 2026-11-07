import io
from collections.abc import Callable
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from research_graph.ml.features import FEATURES, TARGET
from research_graph.models import Prediction
from research_graph.services.recommendation import recommend

Factory = Callable[..., dict[str, Any]]


def upload(client: TestClient, data: bytes, name: str = "model.pkl") -> Any:
    return client.post("/upload-model", files={"file": (name, data, "application/octet-stream")})


def csv_file(frame: pd.DataFrame) -> dict[str, Any]:
    return {"file": ("test.csv", frame.to_csv(index=False).encode(), "text/csv")}


def prediction_count(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(Prediction)) or 0


def test_predict_without_model_returns_409(client: TestClient) -> None:
    response = client.post("/predict", json={"records": [{}]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "model_not_loaded"


def test_upload_model_activates_it_and_predict_works(
    client: TestClient,
    model_bytes: bytes,
    frame: pd.DataFrame,
    session_factory: sessionmaker[Session],
) -> None:
    response = upload(client, model_bytes)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "success"
    assert body["model"]["is_active"] is True
    assert body["model"]["algorithm"] == "LogisticRegression"

    records = frame[FEATURES].head(2).to_dict("records")
    prediction = client.post("/predict", json={"records": records})
    assert prediction.status_code == 200
    result = prediction.json()
    assert result["model_version_id"] == body["model"]["id"]
    assert len(result["predictions"]) == 2
    for item in result["predictions"]:
        assert 0 <= item["probability"] <= 1
        assert item["viral_flag"] in (0, 1)
        assert item["recommendation"] == recommend(item["probability"])
    assert prediction_count(session_factory) == 2


def test_upload_rejects_wrong_extension(client: TestClient, model_bytes: bytes) -> None:
    response = upload(client, model_bytes, name="model.txt")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_upload_rejects_garbage_pkl(client: TestClient) -> None:
    response = upload(client, b"garbage")
    assert response.status_code == 400
    assert "модел" in response.json()["error"]["message"]


def test_second_upload_replaces_active_model_and_activate_switches_back(
    client: TestClient, model_bytes: bytes
) -> None:
    first = upload(client, model_bytes, "first.pkl").json()["model"]
    second = upload(client, model_bytes, "second.pkl").json()["model"]

    models = client.get("/models").json()
    assert [m["id"] for m in models] == [second["id"], first["id"]]
    assert [m["is_active"] for m in models] == [True, False]

    activated = client.post(f"/models/{first['id']}/activate")
    assert activated.status_code == 200
    states = {m["id"]: m["is_active"] for m in client.get("/models").json()}
    assert states == {first["id"]: True, second["id"]: False}


def test_activate_unknown_model_returns_404(client: TestClient) -> None:
    assert client.post("/models/999/activate").status_code == 404


def test_predict_validates_input(client: TestClient) -> None:
    empty = client.post("/predict", json={"records": []})
    assert empty.status_code == 422

    unknown = client.post("/predict", json={"records": [{"not_a_feature": 1}]})
    assert unknown.status_code == 422
    assert unknown.json()["error"]["details"][0]["field"] == "records"

    bad_type = client.post("/predict", json={"records": [{"creator_followers": "abc"}]})
    assert bad_type.status_code == 422

    bad_flag = client.post("/predict", json={"records": [{"weekend_flag": 5}]})
    assert bad_flag.status_code == 422


def test_predict_from_csv_returns_roc_auc_and_rows(
    client: TestClient, model_bytes: bytes, frame: pd.DataFrame
) -> None:
    upload(client, model_bytes)
    response = client.post("/predict-from-csv", files=csv_file(frame), params={"limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["roc_auc"] is not None and body["roc_auc"] > 0.5
    assert body["rows_total"] == len(frame)
    assert body["rows_returned"] == 5
    assert {"predicted_probability", "predicted_viral_flag", "recommendation"} <= set(body["rows"][0])


def test_predict_from_csv_without_target_has_no_roc_auc(
    client: TestClient, model_bytes: bytes, frame: pd.DataFrame
) -> None:
    upload(client, model_bytes)
    response = client.post("/predict-from-csv", files=csv_file(frame.drop(columns=[TARGET])))
    assert response.status_code == 200
    assert response.json()["roc_auc"] is None


def test_predict_from_csv_can_return_csv_file(
    client: TestClient, model_bytes: bytes, frame: pd.DataFrame
) -> None:
    upload(client, model_bytes)
    response = client.post("/predict-from-csv", files=csv_file(frame), params={"format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-roc-auc"] != ""
    result = pd.read_csv(io.StringIO(response.text))
    assert len(result) == len(frame)
    assert "predicted_viral_flag" in result.columns


def test_predict_from_csv_with_missing_columns_returns_400(
    client: TestClient, model_bytes: bytes, frame: pd.DataFrame
) -> None:
    upload(client, model_bytes)
    response = client.post("/predict-from-csv", files=csv_file(frame.drop(columns=["product_price"])))
    assert response.status_code == 400
    assert "product_price" in response.json()["error"]["message"]


def test_predict_from_csv_without_model_returns_409(client: TestClient, frame: pd.DataFrame) -> None:
    response = client.post("/predict-from-csv", files=csv_file(frame))
    assert response.status_code == 409


def test_predict_video_saves_prediction(
    client: TestClient,
    make_video: Factory,
    model_bytes: bytes,
    frame: pd.DataFrame,
    session_factory: sessionmaker[Session],
) -> None:
    upload(client, model_bytes)
    video = make_video("v1", features=frame[FEATURES].iloc[0].to_dict())
    response = client.post(f"/videos/{video['id']}/predict")
    assert response.status_code == 200
    body = response.json()
    assert body["video_id"] == video["id"]
    assert body["recommendation"] == recommend(body["probability"])
    assert prediction_count(session_factory) == 1


def test_predict_video_errors(client: TestClient, make_video: Factory) -> None:
    assert client.post("/videos/999/predict").status_code == 404
    video = make_video("v1")
    response = client.post(f"/videos/{video['id']}/predict")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "model_not_loaded"
