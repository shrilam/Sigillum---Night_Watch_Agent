# On-call Lab

A local-first incident-response sandbox for testing AI on-call agents against a fictional online shop. The simulator has 12 services, replayable incident scenarios, synthetic logs and metrics, safe simulated remediations, and a scored postmortem flow. It uses only Python's standard library and has no production integrations.

## Run

1. Install Python 3.10 or later if it is not already installed.
2. From this folder, run `python server.py`.
3. Open <http://127.0.0.1:8000> in a browser.
4. Stop the local server with Ctrl+C. Use **↻** or the scenario selector to reset/replay.

The server binds to loopback (`127.0.0.1`) only. It does not need Node.js, npm, network access, credentials, or external services. Google Fonts are optional; the UI falls back to system fonts if unavailable.

The home page is a fictional, interactive storefront. Select **Team workspace** to open the incident console. The local demo password is `prathith`. This is a client-side convenience gate for the sandbox only—not secure authentication; do not use it to protect sensitive information or expose the app publicly.

## Migration scaffold (React + FastAPI)

The original sandbox above remains available as a reference. The new `frontend/` and `backend/` projects are an early migration scaffold; currently, the React dashboard reads the seeded checkout scenario and service topology from FastAPI. Investigation, remediation, Ollama, SSE, and SQLite workflows are not implemented yet.

Requirements: Python 3.10+ and Node.js 20+ (npm is included with Node.js). From the repository root, create a Python environment, install backend dependencies, and start FastAPI:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal, install and start the frontend:

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. FastAPI's interactive API documentation is at <http://127.0.0.1:8000/docs>. The Vite development server proxies `/api` requests to the loopback-only backend.

## Scenarios

- **Checkout success rate dropped (SEV-1):** two independent causes—exhausted payment connections and stale inventory cache. Both need their own remediation.
- **Product detail latency elevated (SEV-2):** a hot catalog partition; checkout is intentionally healthy.
- **Order notification queue growing (SEV-2):** consumer capacity below message volume; order placement remains healthy.

The initial alert includes symptoms, not ground truth. The diagnosis candidate list is intentionally shared between scenarios. Ground truth is returned only after a postmortem submission.

## Agent API

All endpoints are on the same origin. Responses are JSON. The active exercise is a single shared simulator session, so teams should use separate local copies/ports for isolated runs.

| Method and path | Purpose |
| --- | --- |
| `GET /api/health` | Simulator health and service count |
| `GET /api/state` | Active alert, service status, elapsed time, actions applied; no hidden causes |
| `GET /api/scenarios` | Scenario IDs and public descriptions |
| `GET /api/services` | Twelve services with dependency edges and current status |
| `GET /api/logs?service=payments&q=timeout` | Evidence logs; both filters are optional |
| `GET /api/metrics?service=payments` | Metric history and labels; service filter optional |
| `GET /api/actions` | Actions allowlisted for this scenario, including an explicitly unsafe option |
| `GET /api/diagnoses` | Shared hypothesis choices for a postmortem; not scenario-specific truth |
| `POST /api/actions` | Apply an allowlisted simulated action: `{"action":"drain-payment-workers"}` |
| `POST /api/postmortem` | Submit `{"summary":"...at least 40 characters...","cause_ids":["payment_pool_exhaustion"]}` |
| `POST /api/reset` | Start/replay a scenario: `{"scenario_id":"checkout-double-fault"}` |

Unknown or unavailable actions are rejected. The retry-amplification option is intentionally blocked without changing service state. Every accepted or rejected remediation attempt is retained in the evidence timeline until reset. Reset restores the scenario to its initial state.

Example agent loop:

1. Read `/api/state`, then inspect relevant `/api/logs`, `/api/metrics`, and `/api/services`.
2. Form hypotheses from `/api/diagnoses`; choose only actions listed by `/api/actions`.
3. Apply a remediation and re-read state/telemetry to verify the result.
4. Submit a concise summary and all suspected cause IDs to `/api/postmortem`.
5. Review the score and revealed ground truth; POST `/api/reset` before the next run.

## Scoring

Diagnosis completeness, remediation completion, and postmortem quality contribute to a 0–100 score. The result reveals actual causes and missing fixes after submission. A run is marked resolved only when all causes are identified and every required safe remediation has been applied. This is a lightweight practice score, not a measure of real-world incident skill.

## Tests

The documented standard-library test command is `python -m unittest discover -s tests -v`, but the test suite has not been added yet; this currently fails because the `tests/` directory does not exist.

## Migration baseline

See [docs/phase-1-baseline.md](docs/phase-1-baseline.md) for the recorded prototype baseline, first implementation slice, safety decisions, and migration checklist.

## Safety and limitations

This is a fictional, in-memory simulator. It has no shell/command execution or integrations to real infrastructure. It is designed for local team experiments, not production incident response. The whole instance shares one active scenario; do not expose its loopback server publicly.