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


def test_meal_estimate_linked_history_and_learning_readiness():
    with TestClient(app) as client:
        profile = client.put(
            "/api/v1/profile",
            json={
                "display_name": "Test",
                "insulin_action_hours": 4,
                "glucose_low_threshold": 70,
                "glucose_high_threshold": 180,
            },
        )
        assert profile.status_code == 200

        regimen = client.put(
            "/api/v1/regimen",
            json=[
                {
                    "start_minute": 0,
                    "basal_units_per_hour": 1,
                    "insulin_carb_ratio": 10,
                    "correction_factor": 40,
                    "target_glucose": 110,
                }
            ],
        )
        assert regimen.status_code == 200

        estimate = client.post(
            "/api/v1/guidance/meal-dose-estimate",
            json={"occurred_at": "2026-07-29T08:00:00Z", "carbs_g": 45},
        )
        assert estimate.status_code == 200
        assert estimate.json()["estimated_units"] == 4.5
        assert "not an AI dose recommendation" in estimate.json()["disclaimer"]

        logged = client.post(
            "/api/v1/logs/meals-with-dose",
            json={
                "meal": {
                    "occurred_at": "2026-07-29T08:00:00Z",
                    "name": "Oatmeal",
                    "carbs_g": 45,
                    "protein_g": 12,
                    "fat_g": 8,
                    "fiber_g": 6,
                    "notes": None,
                },
                "confirmed_units": 4.0,
            },
        )
        assert logged.status_code == 201
        assert logged.json()["dose_id"] is not None

        history = client.get("/api/v1/logs/history")
        assert history.status_code == 200
        linked_doses = [
            item
            for item in history.json()
            if item["item_type"] == "insulin" and item["related_id"] is not None
        ]
        assert linked_doses

        demo = client.post("/api/v1/sample-history")
        assert demo.status_code == 200

        readiness = client.get("/api/v1/insights/readiness")
        assert readiness.status_code == 200
        assert readiness.json()["overnight_nights_ready"] >= 3
        assert readiness.json()["meal_period_counts"]["breakfast"] >= 3

        insights = client.post("/api/v1/insights/generate")
        assert insights.status_code == 200
        assert {item["insight_type"] for item in insights.json()} >= {
            "basal_pattern",
            "ic_ratio_pattern",
        }

        removed = client.delete("/api/v1/sample-history")
        assert removed.status_code == 200
        assert removed.json()["deleted"] > 0
