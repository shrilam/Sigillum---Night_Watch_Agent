from pydantic import BaseModel, Field

from app.models.domain import (
    Evidence,
    Incident,
    IncidentReport,
    Investigation,
    LifecycleEvent,
    MetricSample,
    RemediationPlan,
    ScenarioSnapshot,
    Service,
    VerificationResult,
)


class HealthResponse(BaseModel):
    ok: bool
    name: str
    services: int


class ScenarioRead(BaseModel):
    id: str
    title: str
    severity: str
    summary: str


class InjectRequest(BaseModel):
    scenario_id: str


class ApprovalRequest(BaseModel):
    approved: bool
    approver: str = Field(default="local operator", min_length=1, max_length=80)


class ReportRequest(BaseModel):
    summary: str = ""


class StateResponse(BaseModel):
    scenario_id: str
    incident: Incident
    elapsed_minutes: int
    services: list[Service]
    resolved: bool


ServiceRead = Service
IncidentRead = Incident
MetricRead = MetricSample
EvidenceRead = Evidence
EventRead = LifecycleEvent
InvestigationRead = Investigation
RemediationRead = RemediationPlan
VerificationRead = VerificationResult
ReportRead = IncidentReport


def state_response(snapshot: ScenarioSnapshot) -> StateResponse:
    if snapshot.incident is None:
        raise ValueError("Simulator snapshot has no detected incident")
    return StateResponse(
        scenario_id=snapshot.scenario_id,
        incident=snapshot.incident,
        elapsed_minutes=snapshot.elapsed_minutes,
        services=snapshot.services,
        resolved=snapshot.resolved,
    )
