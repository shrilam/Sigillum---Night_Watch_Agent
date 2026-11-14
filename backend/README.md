# Backend

The API entry point and `create_app()` factory are in `app/main.py`; routers and Pydantic schemas are in `app/api/`. Public service/scenario fixtures and deterministic simulator behavior are isolated in `app/simulator/`.

## Implemented in Phases 3–4

- Typed domain models for incidents, services, telemetry, and evidence.
- Three replayable synthetic scenarios, with metric-threshold incident detection.
- SQLite persistence for current simulator state, incidents, metrics, and evidence.
- Restart recovery for the active scenario and incident.
- REST endpoints for health, services, scenarios, simulator state/injection/reset, incident history/details, metrics, evidence logs, and lifecycle events.
- Pydantic response validation, bounded list queries, and 404/422 errors for invalid lookups/injections.
- Evidence-linked investigation using the configured local Ollama model, with a clearly labeled telemetry-only fallback when Ollama is unavailable or returns invalid data.
- Allowlisted simulated remediation plans, explicit audited approval for medium-risk actions, and rejection of unsafe retry amplification.
- Metric- and service-health-based recovery verification, persisted reports, activity records, and reconnectable SSE lifecycle updates.

## Package boundaries

- `app/core/` — environment settings and application-wide policy.
- `app/models/` — domain models.
- `app/database/` — SQLite schema, persistence, and query methods.
- `app/monitoring/` — metric-based incident detection.
- `app/agent/` — reserved for evidence-backed investigation and remediation planning.
- `app/integrations/` — local Ollama adapter; no external provider integration.

Only real infrastructure integrations are out of scope. All server and Ollama defaults remain loopback-only; no route runs shell commands or reaches production systems.

The default database is `data/nightwatch.db`. Set `NIGHTWATCH_DATABASE_URL` to another local `sqlite:///...` URL for isolated runs. `NIGHTWATCH_HOST` only accepts loopback addresses.
