from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import create_app


def _features_from_model_info(client: TestClient) -> dict[str, float]:
    response = client.get("/model/info")
    response.raise_for_status()
    feature_names = response.json()["features"]
    return {name: 0.0 for name in feature_names}


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_loaded"] is True


def test_score_batch_endpoint() -> None:
    client = TestClient(create_app())
    features = _features_from_model_info(client)
    response = client.post(
        "/score_batch",
        json={
            "items": [
                {
                    "drive_id": "drive-1",
                    "day": str(date(2026, 2, 20)),
                    "features": features,
                }
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()[0]
    assert 0.0 <= payload["risk_score"] <= 1.0
    assert payload["risk_bucket"] in {"LOW", "MED", "HIGH"}
    assert payload["model_version"]


def test_model_info_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/model/info")

    assert response.status_code == 200
    assert response.json()["model_version"]


def test_score_batch_rejects_schema_mismatch() -> None:
    client = TestClient(create_app())
    features = _features_from_model_info(client)
    features.pop(next(iter(features)))
    features["unexpected_feature"] = 1.0

    response = client.post(
        "/score_batch",
        json={
            "items": [
                {
                    "drive_id": "drive-1",
                    "day": str(date(2026, 2, 20)),
                    "features": features,
                }
            ]
        },
    )

    assert response.status_code == 422
    assert "Feature schema mismatch" in response.text
