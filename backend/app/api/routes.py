import asyncio
from datetime import datetime, timezone
import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ApprovalRequest,
    EvidenceRead,
    EventRead,
    HealthResponse,
    IncidentRead,
    IncidentReport,
    InvestigationRead,
    InjectRequest,
    MetricRead,
    RemediationRead,
    ReportRead,
    ReportRequest,
    ScenarioRead,
    ServiceRead,
    StateResponse,
    VerificationRead,
    state_response,
)
from app.agent.investigation import Investigator, build_remediation_plans
from app.integrations.ollama import OllamaClient
from app.models.domain import LifecycleEvent, RemediationPlan
from app.monitoring.verification import RecoveryVerifier
from app.simulator.catalog import SCENARIO_SUMMARIES, SERVICES

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, name="Nightwatch AI", services=len(SERVICES))


@router.get("/services", response_model=list[ServiceRead], tags=["services"])
def list_services(request: Request) -> list[ServiceRead]:
    return request.app.state.snapshot.services


@router.get("/services/{service_id}", response_model=ServiceRead, tags=["services"])
def get_service(service_id: str, request: Request) -> ServiceRead:
    service = next((item for item in request.app.state.snapshot.services if item.id == service_id), None)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/scenarios", response_model=list[ScenarioRead], tags=["simulator"])
def list_scenarios() -> list[ScenarioRead]:
    return [ScenarioRead(**scenario) for scenario in SCENARIO_SUMMARIES]


@router.get("/state", response_model=StateResponse, tags=["simulator"])
def simulator_state(request: Request) -> StateResponse:
    return state_response(request.app.state.snapshot)


@router.post("/simulator/inject", response_model=StateResponse, tags=["simulator"])
def inject_scenario(payload: InjectRequest, request: Request) -> StateResponse:
    simulator = request.app.state.simulator
    detector = request.app.state.detector
    try:
        snapshot = simulator.inject(payload.scenario_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    incident = detector.detect(snapshot)
    if incident is None:
        raise HTTPException(status_code=422, detail="Scenario produced no threshold violations")
    snapshot = simulator.attach_incident(snapshot, incident)
    request.app.state.database.save_snapshot(snapshot)
    request.app.state.snapshot = snapshot
    _publish_activity(request, incident.id, "incident_detected", {"incident_id": incident.id, "severity": incident.severity})
    return state_response(snapshot)


@router.post("/simulator/reset", response_model=StateResponse, tags=["simulator"])
def reset_scenario(payload: InjectRequest, request: Request) -> StateResponse:
    return inject_scenario(payload, request)


@router.get("/incidents", response_model=list[IncidentRead], tags=["incidents"])
def list_incidents(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> list[IncidentRead]:
    return request.app.state.database.list_incidents(limit=limit)


@router.get("/incidents/{incident_id}", response_model=IncidentRead, tags=["incidents"])
def get_incident(incident_id: str, request: Request) -> IncidentRead:
    incident = request.app.state.database.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/metrics", response_model=list[MetricRead], tags=["telemetry"])
def list_metrics(
    request: Request,
    service: str | None = None,
    incident_id: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[MetricRead]:
    return request.app.state.database.list_metrics(service_id=service, incident_id=incident_id, limit=limit)


@router.get("/logs", response_model=list[EvidenceRead], tags=["telemetry"])
def list_evidence(
    request: Request,
    service: str | None = None,
    incident_id: str | None = None,
    q: str = "",
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[EvidenceRead]:
    return request.app.state.database.list_evidence(service_id=service, query_text=q, incident_id=incident_id, limit=limit)


@router.get("/events", response_model=list[EventRead], tags=["events"])
def list_events(
    request: Request,
    incident_id: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
) -> list[EventRead]:
    return request.app.state.database.list_events(incident_id=incident_id, limit=limit)


def _publish_event(request: Request, incident_id: str, event_type: str, payload: dict) -> None:
    event = LifecycleEvent(
        id=f"evt-{uuid4().hex}",
        incident_id=incident_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        payload=payload,
    )
    request.app.state.database.record_event(event)


def _publish_activity(request: Request, incident_id: str, activity_type: str, payload: dict) -> None:
    now = datetime.now(timezone.utc)
    activity_id = f"activity-{uuid4().hex}"
    record = {"id": activity_id, "incident_id": incident_id, "activity_type": activity_type, "created_at": now.isoformat(), **payload}
    request.app.state.database.save_artifact("activity", activity_id, incident_id, now.isoformat(), record)


def _require_active_incident(request: Request, incident_id: str):
    snapshot = request.app.state.snapshot
    if snapshot.incident is None or snapshot.incident.id != incident_id:
        if request.app.state.database.get_incident(incident_id) is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        raise HTTPException(status_code=409, detail="Only the active incident can be changed")
    return snapshot


@router.get("/model/status", tags=["model"])
def model_status(request: Request) -> dict:
    return request.app.state.ollama.status()


@router.get("/model/models", tags=["model"])
def model_list(request: Request) -> dict:
    status = request.app.state.ollama.status()
    return {"available": status["available"], "models": status["models"], "configured_model": status["model"]}


@router.post("/incidents/{incident_id}/investigate", tags=["investigation"])
def investigate_incident(incident_id: str, request: Request) -> dict:
    snapshot = _require_active_incident(request, incident_id)
    existing = request.app.state.database.list_artifacts("investigation", incident_id, limit=1)
    if existing:
        investigation = existing[0]
    else:
        result = Investigator(request.app.state.settings).investigate(snapshot)
        investigation = result.model_dump(mode="json")
        request.app.state.database.save_artifact("investigation", f"investigation-{incident_id}", incident_id, result.created_at.isoformat(), investigation)
        _publish_event(request, incident_id, "investigation.completed", {"provider": result.provider})
        _publish_activity(request, incident_id, "investigation_completed", {"provider": result.provider})

    plans = request.app.state.database.list_artifacts("remediation", incident_id, limit=50)
    if not plans:
        for plan in build_remediation_plans(snapshot.incident):
            record = plan.model_dump(mode="json")
            request.app.state.database.save_artifact("remediation", plan.id, incident_id, plan.created_at.isoformat(), record)
            plans.append(record)
    return {"investigation": investigation, "remediations": plans}


@router.get("/remediation", response_model=list[RemediationRead], tags=["remediation"])
def list_remediations(request: Request, incident_id: str | None = None) -> list[RemediationRead]:
    return [RemediationPlan.model_validate(item) for item in request.app.state.database.list_artifacts("remediation", incident_id, limit=500)]


@router.post("/remediation/{remediation_id}/approve", response_model=RemediationRead, tags=["remediation"])
def approve_remediation(remediation_id: str, payload: ApprovalRequest, request: Request) -> RemediationRead:
    raw = request.app.state.database.get_artifact("remediation", remediation_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Remediation plan not found")
    plan = RemediationPlan.model_validate(raw)
    _require_active_incident(request, plan.incident_id)
    if plan.status in {"blocked", "executed"}:
        raise HTTPException(status_code=409, detail=f"Remediation is {plan.status}")
    if not plan.approval_required:
        raise HTTPException(status_code=409, detail="This low-risk action does not require approval")
    now = datetime.now(timezone.utc)
    plan = plan.model_copy(update={
        "approved": payload.approved,
        "approved_by": payload.approver,
        "approval_at": now,
        "status": "approved" if payload.approved else "blocked",
    })
    record = plan.model_dump(mode="json")
    request.app.state.database.save_artifact("remediation", plan.id, plan.incident_id, plan.created_at.isoformat(), record)
    _publish_event(request, plan.incident_id, "remediation.approved" if payload.approved else "remediation.rejected", {"remediation_id": plan.id, "approver": payload.approver})
    _publish_activity(request, plan.incident_id, "remediation_approval", {"remediation_id": plan.id, "approved": payload.approved, "approver": payload.approver})
    return plan


@router.post("/remediation/{remediation_id}/execute", tags=["remediation"])
def execute_remediation(remediation_id: str, request: Request) -> dict:
    raw = request.app.state.database.get_artifact("remediation", remediation_id)
    if raw is None:
        raise HTTPException(status_code=404, detail="Remediation plan not found")
    plan = RemediationPlan.model_validate(raw)
    snapshot = _require_active_incident(request, plan.incident_id)
    if plan.status == "executed":
        return {"ok": True, "plan": plan, "state": state_response(snapshot)}
    if plan.status == "blocked":
        raise HTTPException(status_code=409, detail="Blocked actions cannot execute")
    if plan.approval_required and not plan.approved:
        raise HTTPException(status_code=409, detail="Explicit approval is required before execution")
    try:
        updated = request.app.state.simulator.apply_action(snapshot, plan.action_id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    now = datetime.now(timezone.utc)
    plan = plan.model_copy(update={"status": "executed", "executed_at": now})
    request.app.state.database.save_artifact("remediation", plan.id, plan.incident_id, plan.created_at.isoformat(), plan.model_dump(mode="json"))
    request.app.state.database.save_snapshot(updated)
    request.app.state.snapshot = updated
    _publish_event(request, plan.incident_id, "remediation.executed", {"remediation_id": plan.id, "action_id": plan.action_id})
    _publish_activity(request, plan.incident_id, "remediation_executed", {"remediation_id": plan.id, "action_id": plan.action_id})
    return {"ok": True, "plan": plan, "state": state_response(updated)}


@router.post("/incidents/{incident_id}/verify", response_model=VerificationRead, tags=["verification"])
def verify_incident(incident_id: str, request: Request) -> VerificationRead:
    snapshot = _require_active_incident(request, incident_id)
    result = RecoveryVerifier().verify(snapshot)
    updated = request.app.state.simulator.update_status(snapshot, "Resolved" if result.resolved else "Mitigating", result.resolved)
    request.app.state.database.save_snapshot(updated)
    request.app.state.snapshot = updated
    request.app.state.database.save_artifact("verification", result.id, incident_id, result.created_at.isoformat(), result.model_dump(mode="json"))
    _publish_event(request, incident_id, "recovery.verified", {"passed": result.passed, "resolved": result.resolved})
    _publish_activity(request, incident_id, "recovery_verification", {"passed": result.passed, "resolved": result.resolved})
    return result


@router.post("/incidents/{incident_id}/report", response_model=ReportRead, tags=["reports"])
def create_incident_report(incident_id: str, payload: ReportRequest, request: Request) -> ReportRead:
    snapshot = _require_active_incident(request, incident_id)
    if snapshot.incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    investigation = request.app.state.database.list_artifacts("investigation", incident_id, limit=1)
    verification_rows = request.app.state.database.list_artifacts("verification", incident_id, limit=1)
    verification = VerificationRead.model_validate(verification_rows[0]) if verification_rows else None
    actions = [item for item in snapshot.applied_actions]
    findings = list(investigation[0].get("facts", [])) if investigation else [snapshot.incident.summary]
    if investigation:
        findings.extend(hypothesis["statement"] for hypothesis in investigation[0].get("hypotheses", []))
    report = IncidentReport(
        id=f"report-{uuid4().hex[:12]}",
        incident_id=incident_id,
        title=f"Incident report: {snapshot.incident.title}",
        summary=payload.summary.strip() or snapshot.incident.summary,
        findings=findings,
        evidence_ids=[item.id for item in snapshot.evidence],
        actions=actions,
        verification=verification,
        created_at=datetime.now(timezone.utc),
    )
    request.app.state.database.save_artifact("report", report.id, incident_id, report.created_at.isoformat(), report.model_dump(mode="json"))
    _publish_event(request, incident_id, "report.created", {"report_id": report.id})
    _publish_activity(request, incident_id, "report_created", {"report_id": report.id})
    return report


@router.get("/reports/{report_id}", response_model=ReportRead, tags=["reports"])
def get_report(report_id: str, request: Request) -> ReportRead:
    payload = request.app.state.database.get_artifact("report", report_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Incident report not found")
    return IncidentReport.model_validate(payload)


@router.get("/agent/activity", tags=["activity"])
def agent_activity(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> list[dict]:
    return request.app.state.database.list_artifacts("activity", limit=limit)


@router.get("/events/stream", tags=["events"])
async def stream_events(request: Request) -> StreamingResponse:
    async def generate():
        sent: set[str] = set()
        last_id = request.headers.get("last-event-id")
        while not await request.is_disconnected():
            events = list(reversed(request.app.state.database.list_events(limit=200)))
            past_last_id = last_id is None
            if last_id and any(event.id == last_id for event in events):
                for event in events:
                    if event.id == last_id:
                        past_last_id = True
                        continue
                    if not past_last_id:
                        continue
                    if event.id in sent:
                        continue
                    sent.add(event.id)
                    data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                    yield f"id: {event.id}\nevent: {event.event_type}\ndata: {data}\n\n"
            else:
                for event in events:
                    if event.id in sent:
                        continue
                    sent.add(event.id)
                    data = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)
                    yield f"id: {event.id}\nevent: {event.event_type}\ndata: {data}\n\n"
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
