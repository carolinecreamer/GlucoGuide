from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profile_validation_rejects_unsafe_threshold():
    with TestClient(app) as client:
        response = client.put(
            "/api/v1/profile",
            json={
                "display_name": "Test",
                "insulin_action_hours": 4,
                "glucose_low_threshold": 30,
                "glucose_high_threshold": 180,
            },
        )

    assert response.status_code == 422
