from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.main import create_app


FEATURES = {
    "age_days": 112.0,
    "smart_5_mean_7d": 7.0,
    "smart_5_slope_14d": 0.2,
    "smart_197_max_30d": 12.0,
    "smart_197_mean_7d": 5.0,
    "smart_198_delta_7d": 1.0,
    "smart_199_volatility_30d": 2.0,
    "temperature_mean_7d": 36.0,
    "read_latency_mean_7d": 5.5,
    "write_latency_mean_7d": 7.1,
    "missing_smart_197_30d": 0.0,
}


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["model_loaded"] is True


def test_score_batch_endpoint() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/score_batch",
        json={
            "items": [
                {
                    "drive_id": "drive-1",
                    "day": str(date(2026, 2, 20)),
                    "features": FEATURES,
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
