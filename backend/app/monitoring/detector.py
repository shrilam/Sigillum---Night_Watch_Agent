from datetime import datetime, timezone
from uuid import uuid4

from app.models.domain import Incident, MetricSample, ScenarioSnapshot
from app.simulator.catalog import SCENARIOS


SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def metric_breached(metric: MetricSample) -> bool:
    if metric.operator == "gt":
        return metric.value > metric.threshold
    if metric.operator == "gte":
        return metric.value >= metric.threshold
    if metric.operator == "lt":
        return metric.value < metric.threshold
    return metric.value <= metric.threshold


class IncidentDetector:
    """Detect incidents from observed synthetic telemetry, not hidden scenario truth."""

    def detect(self, snapshot: ScenarioSnapshot) -> Incident | None:
        breached = [metric for metric in snapshot.metrics if metric_breached(metric)]
        if not breached:
            return None

        scenario = SCENARIOS[snapshot.scenario_id]
        severity = max(
            (metric.breach_severity for metric in breached),
            key=SEVERITY_RANK.__getitem__,
        )
        affected = sorted({metric.service_id for metric in breached})
        now = datetime.now(timezone.utc)
        return Incident(
            id=f"inc-{uuid4().hex[:12]}",
            scenario_id=snapshot.scenario_id,
            title=scenario["title"],
            severity=severity,
            status="Investigating",
            trigger=scenario["trigger"],
            impact=scenario["impact"],
            summary=scenario["summary"],
            affected_services=affected,
            created_at=now,
            updated_at=now,
        )
