from typing import Literal

from pydantic import BaseModel, ConfigDict


ServiceStatus = Literal["healthy", "degraded", "critical"]
Severity = Literal["Critical", "High", "Medium", "Low"]


class HealthResponse(BaseModel):
    ok: bool
    name: str
    services: int


class ServiceRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    group: str
    depends_on: list[str]
    status: ServiceStatus


class IncidentRead(BaseModel):
    id: str
    title: str
    severity: Severity
    status: str
    trigger: str
    impact: str
    summary: str


class ScenarioRead(BaseModel):
    id: str
    title: str
    severity: Severity
    summary: str


class StateResponse(BaseModel):
    scenario_id: str
    incident: IncidentRead
    elapsed_minutes: int
    services: list[ServiceRead]
    resolved: bool
