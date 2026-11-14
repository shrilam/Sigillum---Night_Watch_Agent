from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ServiceStatus = Literal["healthy", "degraded", "critical"]
Severity = Literal["Critical", "High", "Medium", "Low"]
MetricOperator = Literal["gt", "gte", "lt", "lte"]
EvidenceLevel = Literal["info", "warning", "error"]


class Service(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    group: str
    depends_on: list[str] = Field(default_factory=list)
    status: ServiceStatus = "healthy"


class MetricSample(BaseModel):
    service_id: str
    name: str
    value: float
    unit: str
    threshold: float
    operator: MetricOperator
    breach_severity: Severity
    observed_at: datetime


class Evidence(BaseModel):
    id: str
    incident_id: str
    service_id: str
    level: EvidenceLevel
    message: str
    observed_at: datetime
    source: str = "simulator-log"


class LifecycleEvent(BaseModel):
    id: str
    incident_id: str
    event_type: str
    occurred_at: datetime
    payload: dict = Field(default_factory=dict)


class Hypothesis(BaseModel):
    id: str
    statement: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    caveat: str = ""


class Investigation(BaseModel):
    incident_id: str
    provider: str
    summary: str
    facts: list[str] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    created_at: datetime


class RemediationPlan(BaseModel):
    id: str
    incident_id: str
    action_id: str
    title: str
    description: str
    target_service: str
    reason: str
    expected_outcome: str
    risk: Literal["low", "medium", "high"]
    approval_required: bool
    approved: bool = False
    approved_by: str | None = None
    approval_at: datetime | None = None
    status: Literal["pending_approval", "approved", "executed", "blocked"] = "approved"
    created_at: datetime
    executed_at: datetime | None = None


class VerificationCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class VerificationResult(BaseModel):
    id: str
    incident_id: str
    passed: bool
    resolved: bool
    checks: list[VerificationCheck]
    created_at: datetime


class IncidentReport(BaseModel):
    id: str
    incident_id: str
    title: str
    summary: str
    findings: list[str]
    evidence_ids: list[str] = Field(default_factory=list)
    actions: list[str]
    verification: VerificationResult | None = None
    created_at: datetime


class Incident(BaseModel):
    id: str
    scenario_id: str
    title: str
    severity: Severity
    status: str = "Investigating"
    trigger: str
    impact: str
    summary: str
    affected_services: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ScenarioSnapshot(BaseModel):
    scenario_id: str
    elapsed_minutes: int
    services: list[Service]
    metrics: list[MetricSample]
    evidence: list[Evidence]
    incident: Incident | None = None
    resolved: bool = False
    applied_actions: list[str] = Field(default_factory=list)
