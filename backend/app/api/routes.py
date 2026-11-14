from fastapi import APIRouter

from app.api.schemas import HealthResponse, ScenarioRead, ServiceRead, StateResponse
from app.simulator.catalog import CHECKOUT_SCENARIO, SCENARIOS, SERVICES

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(ok=True, name="Nightwatch AI", services=len(SERVICES))


@router.get("/services", response_model=list[ServiceRead], tags=["services"])
def list_services() -> list[ServiceRead]:
    statuses = CHECKOUT_SCENARIO["service_status"]
    return [
        ServiceRead(**service, status=statuses.get(service["id"], "healthy"))
        for service in SERVICES
    ]


@router.get("/scenarios", response_model=list[ScenarioRead], tags=["simulator"])
def list_scenarios() -> list[ScenarioRead]:
    return [ScenarioRead(**scenario) for scenario in SCENARIOS]


@router.get("/state", response_model=StateResponse, tags=["simulator"])
def simulator_state() -> StateResponse:
    incident = {
        key: CHECKOUT_SCENARIO[key]
        for key in ("id", "title", "severity", "status", "trigger", "impact", "summary")
    }
    incident["id"] = CHECKOUT_SCENARIO["id"]
    return StateResponse(
        scenario_id=CHECKOUT_SCENARIO["id"],
        incident=incident,
        elapsed_minutes=CHECKOUT_SCENARIO["elapsed_minutes"],
        services=list_services(),
        resolved=False,
    )
