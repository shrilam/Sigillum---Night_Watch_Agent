from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_local_simulator() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "name": "Nightwatch AI", "services": 12}


def test_services_returns_twelve_seeded_services() -> None:
    response = client.get("/api/services")

    assert response.status_code == 200
    services = response.json()
    assert len(services) == 12
    assert {service["id"] for service in services} >= {"checkout", "payments", "inventory"}
    assert next(service for service in services if service["id"] == "checkout")["status"] == "critical"


def test_state_exposes_symptoms_without_hidden_ground_truth() -> None:
    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"] == "checkout-double-fault"
    assert payload["incident"]["title"] == "Checkout success rate dropped"
    assert "causes" not in payload["incident"]
    assert payload["resolved"] is False


def test_scenarios_returns_public_fixture_only() -> None:
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 1
    assert scenarios[0]["id"] == "checkout-double-fault"
    assert "causes" not in scenarios[0]
