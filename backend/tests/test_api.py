import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.api.routes import stream_events
from app.main import create_app



@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as test_client:
        yield test_client


def test_health_reports_local_simulator(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "name": "Nightwatch AI", "services": 12}


def test_services_returns_twelve_seeded_services(client: TestClient) -> None:
    response = client.get("/api/services")

    assert response.status_code == 200
    services = response.json()
    assert len(services) == 12
    assert {service["id"] for service in services} >= {"checkout", "payments", "inventory"}
    assert next(service for service in services if service["id"] == "checkout")["status"] == "critical"


def test_state_exposes_symptoms_without_hidden_ground_truth(client: TestClient) -> None:
    response = client.get("/api/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"] == "checkout-double-fault"
    assert payload["incident"]["title"] == "Checkout success rate dropped"
    assert "causes" not in payload["incident"]
    assert payload["resolved"] is False


def test_scenarios_returns_public_fixture_only(client: TestClient) -> None:
    response = client.get("/api/scenarios")

    assert response.status_code == 200
    scenarios = response.json()
    assert {scenario["id"] for scenario in scenarios} == {
        "checkout-double-fault",
        "catalog-hot-partition",
        "notification-lag",
    }
    assert all("causes" not in scenario for scenario in scenarios)


@pytest.mark.parametrize(
    ("scenario_id", "title", "minimum_severity"),
    [
        ("checkout-double-fault", "Checkout success rate dropped", "Critical"),
        ("catalog-hot-partition", "Product detail latency elevated", "Critical"),
        ("notification-lag", "Order notification queue growing", "High"),
    ],
)
def test_injection_detects_incident_from_metrics(
    client: TestClient,
    scenario_id: str,
    title: str,
    minimum_severity: str,
) -> None:
    response = client.post("/api/simulator/inject", json={"scenario_id": scenario_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"] == scenario_id
    assert payload["incident"]["title"] == title
    assert payload["incident"]["severity"] == minimum_severity
    assert payload["incident"]["affected_services"]
    assert "causes" not in payload["incident"]


def test_detail_and_telemetry_endpoints_return_saved_evidence(client: TestClient) -> None:
    state = client.get("/api/state").json()
    incident_id = state["incident"]["id"]

    detail = client.get(f"/api/services/checkout")
    incident = client.get(f"/api/incidents/{incident_id}")
    metrics = client.get("/api/metrics?service=checkout")
    evidence = client.get("/api/logs?service=payments&q=connection")

    assert detail.status_code == 200 and detail.json()["status"] == "critical"
    assert incident.status_code == 200 and incident.json()["id"] == incident_id
    assert any(item["name"] == "success_rate" for item in metrics.json())
    assert len(evidence.json()) == 1
    assert {item["event_type"] for item in client.get(f"/api/events?incident_id={incident_id}").json()} == {
        "scenario.injected",
        "incident.detected",
    }


def test_unknown_service_incident_and_scenario_have_clear_errors(client: TestClient) -> None:
    assert client.get("/api/services/missing").status_code == 404
    assert client.get("/api/incidents/missing").status_code == 404
    assert client.post("/api/simulator/inject", json={"scenario_id": "missing"}).status_code == 404


def test_incident_and_current_simulator_state_survive_app_restart(tmp_path) -> None:
    database_path = tmp_path / "persistent.db"
    with TestClient(create_app(database_path)) as first_client:
        injected = first_client.post(
            "/api/simulator/inject", json={"scenario_id": "notification-lag"}
        ).json()
        incident_id = injected["incident"]["id"]
        assert len(first_client.get("/api/logs").json()) >= 5

    with TestClient(create_app(database_path)) as restarted_client:
        restored = restarted_client.get("/api/state").json()
        history = restarted_client.get("/api/incidents").json()
        assert restored["scenario_id"] == "notification-lag"
        assert restored["incident"]["id"] == incident_id
        assert any(item["id"] == incident_id for item in history)
        assert len(restarted_client.get("/api/metrics?service=notifications").json()) == 2
        assert len(restarted_client.get(f"/api/events?incident_id={incident_id}").json()) == 2


def test_checkout_lifecycle_blocks_unsafe_and_verifies_both_safe_fixes(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.agent.investigation.OllamaClient.generate_json", lambda *_args, **_kwargs: None)
    state = client.get("/api/state").json()
    incident_id = state["incident"]["id"]
    result = client.post(f"/api/incidents/{incident_id}/investigate").json()
    plans = {plan["action_id"]: plan for plan in result["remediations"]}
    assert result["investigation"]["provider"] == "local-rules-fallback"
    assert plans["increase-checkout-retries"]["status"] == "blocked"

    blocked = client.post(f"/api/remediation/{plans['increase-checkout-retries']['id']}/execute")
    assert blocked.status_code == 409
    assert client.get("/api/state").json()["incident"]["id"] == incident_id

    client.post(f"/api/remediation/{plans['drain-payment-workers']['id']}/execute").raise_for_status()
    metric_count = len(client.get(f"/api/metrics?incident_id={incident_id}").json())
    partial = client.post(f"/api/incidents/{incident_id}/verify").json()
    assert not partial["resolved"]
    assert len(client.get(f"/api/metrics?incident_id={incident_id}").json()) == metric_count

    client.post(f"/api/remediation/{plans['refresh-inventory-cache']['id']}/execute").raise_for_status()
    verified = client.post(f"/api/incidents/{incident_id}/verify").json()
    assert verified["resolved"]
    report = client.post(f"/api/incidents/{incident_id}/report", json={"summary": "Both independent simulated faults were fixed and recovery checks passed."})
    assert report.status_code == 200
    assert client.get(f"/api/reports/{report.json()['id']}").json()["verification"]["resolved"]
    with TestClient(create_app(client.app.state.database.path)) as restarted:
        persisted_report = restarted.get(f"/api/reports/{report.json()['id']}")
        assert persisted_report.status_code == 200
        assert persisted_report.json()["evidence_ids"]


def test_risky_remediation_requires_audited_approval(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.agent.investigation.OllamaClient.generate_json", lambda *_args, **_kwargs: None)
    state = client.post("/api/simulator/inject", json={"scenario_id": "catalog-hot-partition"}).json()
    incident_id = state["incident"]["id"]
    plans = client.post(f"/api/incidents/{incident_id}/investigate").json()["remediations"]
    plan = next(item for item in plans if item["action_id"] == "rebalance-catalog-index")

    assert client.post(f"/api/remediation/{plan['id']}/execute").status_code == 409
    approved = client.post(
        f"/api/remediation/{plan['id']}/approve",
        json={"approved": True, "approver": "on-call operator"},
    )
    assert approved.status_code == 200
    assert approved.json()["approved_by"] == "on-call operator"
    assert client.post(f"/api/remediation/{plan['id']}/execute").status_code == 200
    assert client.post(f"/api/incidents/{incident_id}/verify").json()["resolved"]


def test_model_status_reports_local_ollama_unavailable_without_crashing(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.integrations.ollama.OllamaClient.status", lambda *_args, **_kwargs: {
        "available": False, "model": "qwen2.5-coder:7b", "models": [], "error": "connection refused"
    })

    status = client.get("/api/model/status")
    models = client.get("/api/model/models")
    assert status.status_code == 200 and not status.json()["available"]
    assert models.status_code == 200 and models.json()["models"] == []


def test_sse_stream_replays_lifecycle_events(client: TestClient) -> None:
    request = SimpleNamespace(app=client.app, headers={})
    request.is_disconnected = _connected_request
    async def first_frame() -> str:
        response = await stream_events(request)
        iterator = response.body_iterator
        frame = await anext(iterator)
        await iterator.aclose()
        return response.media_type, frame

    media_type, frame = asyncio.run(first_frame())
    assert media_type == "text/event-stream"
    assert "event: scenario.injected\n" in frame
    assert "data: {" in frame


async def _connected_request() -> bool:
    return False
