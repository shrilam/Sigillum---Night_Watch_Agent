from datetime import datetime, timezone
from uuid import uuid4

from app.models.domain import Evidence, Incident, MetricSample, ScenarioSnapshot, Service
from app.simulator.catalog import ACTION_CATALOG, SCENARIOS, SERVICES


class Simulator:
    """Build deterministic synthetic telemetry snapshots; never touches real services."""

    def inject(self, scenario_id: str) -> ScenarioSnapshot:
        scenario = SCENARIOS.get(scenario_id)
        if scenario is None:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        now = datetime.now(timezone.utc)
        statuses = scenario["service_status"]
        services = [
            Service(**service, status=statuses.get(service["id"], "healthy"))
            for service in SERVICES
        ]
        metrics = [MetricSample(**metric, observed_at=now) for metric in scenario["metrics"]]
        return ScenarioSnapshot(
            scenario_id=scenario_id,
            elapsed_minutes=scenario["elapsed_minutes"],
            services=services,
            metrics=metrics,
            evidence=[],
        )

    def attach_incident(self, snapshot: ScenarioSnapshot, incident: Incident) -> ScenarioSnapshot:
        scenario = SCENARIOS[snapshot.scenario_id]
        now = datetime.now(timezone.utc)
        evidence = [
            Evidence(
                id=str(uuid4()),
                incident_id=incident.id,
                service_id=service_id,
                level=level,
                message=message,
                observed_at=now,
            )
            for service_id, level, message in scenario["evidence"]
        ]
        return snapshot.model_copy(update={"incident": incident, "evidence": evidence})

    def apply_action(self, snapshot: ScenarioSnapshot, action_id: str) -> ScenarioSnapshot:
        scenario = SCENARIOS[snapshot.scenario_id]
        action = ACTION_CATALOG.get(action_id)
        if action_id not in scenario["action_options"] or action is None:
            raise ValueError("Action is not allowlisted for this incident")
        if action.get("unsafe"):
            raise ValueError("Unsafe action is blocked; simulator state was not changed")
        if action_id in snapshot.applied_actions:
            return snapshot

        applied = [*snapshot.applied_actions, action_id]
        now = datetime.now(timezone.utc)
        metrics = [
            metric.model_copy(update={"value": self._recovered_value(metric) if metric.service_id == action["target_service"] else metric.value, "observed_at": now})
            for metric in snapshot.metrics
        ]

        if set(scenario["actions"]).issubset(applied):
            metrics = [
                metric.model_copy(update={"value": self._recovered_value(metric), "observed_at": now})
                for metric in metrics
            ]
        services = [service.model_copy(update={"status": "healthy"}) for service in snapshot.services] if set(scenario["actions"]).issubset(applied) else [
            service.model_copy(update={"status": "healthy"}) if service.id == action["target_service"] else service
            for service in snapshot.services
        ]
        evidence = list(snapshot.evidence)
        if snapshot.incident is not None:
            evidence.append(Evidence(
                id=str(uuid4()),
                incident_id=snapshot.incident.id,
                service_id=action["target_service"],
                level="info",
                message=f"Simulated remediation applied: {action['title']}",
                observed_at=now,
                source="simulator-action",
            ))
        return snapshot.model_copy(update={"applied_actions": applied, "metrics": metrics, "services": services, "evidence": evidence})

    @staticmethod
    def _recovered_value(metric: MetricSample) -> float:
        if metric.operator in {"gt", "gte"}:
            return metric.threshold * 0.5
        recovered = metric.threshold + max(1, abs(metric.threshold) * 0.1)
        return min(100, recovered) if metric.unit == "%" else recovered

    @staticmethod
    def update_status(snapshot: ScenarioSnapshot, status: str, resolved: bool) -> ScenarioSnapshot:
        if snapshot.incident is None:
            return snapshot
        now = datetime.now(timezone.utc)
        incident = snapshot.incident.model_copy(update={"status": status, "updated_at": now})
        return snapshot.model_copy(update={"incident": incident, "resolved": resolved})

    def restore(self, payload: dict) -> ScenarioSnapshot:
        return ScenarioSnapshot.model_validate(payload)

    def serialize(self, snapshot: ScenarioSnapshot) -> dict:
        return snapshot.model_dump(mode="json")
