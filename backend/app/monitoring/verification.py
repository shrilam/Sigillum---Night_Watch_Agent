from datetime import datetime, timezone
from uuid import uuid4

from app.models.domain import ScenarioSnapshot, VerificationCheck, VerificationResult
from app.monitoring.detector import metric_breached
from app.simulator.catalog import SCENARIOS


class RecoveryVerifier:
    def verify(self, snapshot: ScenarioSnapshot) -> VerificationResult:
        incident = snapshot.incident
        if incident is None:
            raise ValueError("An active incident is required for verification")
        required_actions = set(SCENARIOS[snapshot.scenario_id]["actions"])
        applied = set(snapshot.applied_actions)
        actions_passed = required_actions.issubset(applied)
        metrics_passed = not any(metric_breached(metric) for metric in snapshot.metrics)
        services_passed = all(service.status == "healthy" for service in snapshot.services)
        checks = [
            VerificationCheck(
                name="required_remediations",
                passed=actions_passed,
                detail="All required simulated actions applied." if actions_passed else f"Still required: {', '.join(sorted(required_actions - applied)) or 'none'}.",
            ),
            VerificationCheck(
                name="metric_thresholds",
                passed=metrics_passed,
                detail="No current metric violates its recovery threshold." if metrics_passed else "One or more current metrics still violate thresholds.",
            ),
            VerificationCheck(
                name="service_health",
                passed=services_passed,
                detail="All simulated services report healthy." if services_passed else "At least one simulated service remains degraded or critical.",
            ),
        ]
        resolved = all(check.passed for check in checks)
        return VerificationResult(
            id=f"ver-{uuid4().hex[:12]}",
            incident_id=incident.id,
            passed=resolved,
            resolved=resolved,
            checks=checks,
            created_at=datetime.now(timezone.utc),
        )
