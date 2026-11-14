# Nightwatch AI Memory Bank

## 1. Product objective
Build Nightwatch AI as a local-first autonomous SRE and incident response platform that continuously monitors infrastructure, detects incidents, investigates root causes, recommends safe remediations, executes approved actions, and verifies recovery. The system must run locally with Ollama and a local LLM instead of depending on cloud AI APIs.

## 2. Problem statement
Teams need a fast, reliable AI-powered on-call assistant that explains incidents in plain language, correlates failing services, recommends safe remediations, and helps verify whether recovery actually worked. This must work within a local development environment without external paid dependencies.

## 3. Solution overview
Nightwatch AI combines a local monitoring simulator, incident detection logic, AI investigation, structured evidence handling, remediation approvals, and persistent reporting. The prototype focuses on a realistic local loop that simulates monitored services and produces a complete incident lifecycle end-to-end.

## 4. Required technology stack
- Frontend: React + TypeScript + Vite
- Styling: CSS with preserved Nightwatch dark operations aesthetic
- Icons: Lucide React
- Charts: Recharts
- Backend: Python + FastAPI
- API: REST + SSE
- AI: Ollama with Qwen2.5-Coder 7B
- Database: SQLite
- Validation: Pydantic
- Testing: Pytest + Vitest
- Version control: Git

## 5. Core user experience goals
- Premium dark operations dashboard
- Real-time visibility into service health and incidents
- Clear evidence-backed AI investigation
- Safe approval workflow before risky remediations
- Recovery verification driven by metrics rather than command success alone
- Persistent system history for incidents and reports

## 6. Functional requirements
### 6.1 Infrastructure monitoring
- Monitor at least 12 interconnected simulated services
- Track service health, CPU, memory, request rate, error rate, latency, uptime, and last health-check
- Perform periodic checks and detect threshold violations
- Detect abnormal patterns and service failure states
- Support configurable failure injection
- Simulate cascading failures and dependency issues

### 6.2 Incident detection
- Detect service outages, high latency, CPU exhaustion, memory exhaustion, elevated error rates, dependency failures, queue issues, and cascading problems
- Each incident includes ID, title, description, severity, affected services, timestamp, triggering metrics, logs, status, and investigation history
- Severity values: Critical, High, Medium, Low

### 6.3 AI investigation
- Receive incident events and identify relevant services
- Collect metrics, logs, and events
- Correlate failures across services
- Generate and rank root-cause hypotheses
- Associate confidence scores and evidence
- Explain uncertainty when evidence is incomplete
- Separate confirmed facts from hypotheses
- Never invent logs, metrics, or successful actions

### 6.4 Remediation
- Support simulated restart, rollback, queue clear, scaling, resource limit adjustments, and config restoration
- Every action includes an action ID, target service, description, reason, expected outcome, risk, approval requirement, and execution status
- Require explicit approval for risky or destructive actions
- Use a strict allowlist of executable actions
- Validate parameters strictly
- Audit all actions and failures

### 6.5 Recovery verification
- Recheck the affected service after a remediation action
- Compare pre/post metrics
- Verify that the failure condition has cleared
- Detect any new issues introduced by the remediation
- Update the incident status appropriately
- Do not mark as resolved based only on command return success

### 6.6 Persistence and storage
Store the following in SQLite:
- Service info
- Historical metrics
- Incidents
- Events
- Logs
- AI investigation results
- Root-cause hypotheses
- Remediation plans
- Execution history
- Verification results
- Incident reports
- Agent activity history

## 7. API requirements
The backend must expose the following documented FastAPI routes:
- GET /api/health
- GET /api/services
- GET /api/services/{id}
- GET /api/metrics
- GET /api/incidents
- GET /api/incidents/{id}
- POST /api/incidents/{id}/investigate
- GET /api/agent/activity
- GET /api/events/stream
- GET /api/remediation
- POST /api/remediation/{id}/approve
- POST /api/remediation/{id}/execute
- GET /api/reports/{id}
- GET /api/model/status
- GET /api/model/models

All routes must validate payloads, return proper HTTP status codes, include error handling, and be documented.

## 8. Real-time communication requirements
- Use SSE for service health updates, incidents, metric changes, agent progress, evidence collection, diagnosis updates, remediation status, and recovery verification
- Ensure reconnect behavior is graceful when the event stream drops
- Keep the frontend in sync without refreshes

## 9. Local AI requirements
- Ollama must run locally at http://localhost:11434
- Model used: Qwen2.5-Coder 7B
- FastAPI must validate model availability and connection health
- Requests to Ollama must use structured incident context
- Responses must be parsed as structured JSON and validated with Pydantic
- Invalid JSON, timeouts, and connection failures must be handled cleanly
- Investigation context and output records must be preserved

## 10. Security and safety rules
- Validate all API inputs
- Treat logs and events as untrusted data
- Protect against prompt injection
- Keep logs from overriding system instructions
- Validate AI-generated remediation proposals
- Restrict executable actions to an explicit allowlist
- Require approval for destructive or risky actions
- Prevent arbitrary command execution
- Keep secrets out of source control
- Record remediation decisions and execution audit trails
- Separate diagnosis permissions from execution permissions

## 11. Testing requirements
The project must include automated tests for:
- API endpoints
- Database operations
- Service monitoring
- Incident detection
- Incident creation
- AI parsing
- Diagnosis validation
- Remediation approval
- Remediation execution
- Recovery verification
- Frontend components
- Frontend API integration
- Real-time event handling
- End-to-end simulated incident lifecycle

## 12. Project structure
nightwatch-ai/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── styles/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── database/
│   │   ├── monitoring/
│   │   ├── simulator/
│   │   ├── agent/
│   │   └── integrations/
│   ├── tests/
│   └── requirements.txt
├── data/
├── docs/
├── scripts/
├── .env.example
├── .gitignore
└── README.md

## 13. Prototype implementation goals
The working prototype must demonstrate:
1. Startup of local frontend and backend
2. Connection to Ollama and verification of the model
3. Display of 12 simulated services
4. Deliberately injected service failure
5. Automated incident creation
6. AI investigation trigger
7. Evidence collection and analysis
8. Likely root-cause explanation
9. Remediation recommendation
10. User approval flow
11. Simulated remediation execution
12. Recovery verification
13. Real-time dashboard updates
14. Incident report generation
15. SQLite persistence of workflow history

## 14. Non-goals for the prototype
- Real production infrastructure management
- Real cloud or vendor APIs
- Multi-user enterprise permissions
- Production-scale orchestration outside the simulation boundary

## 15. Design and UI principles
- Premium dark operations center aesthetic
- Deep navy/charcoal backgrounds
- Clear hierarchy and restrained accent colors
- Smooth transitions and meaningful motion
- Responsive desktop and tablet layouts
- Useful status indicators and severity color logic
- Functional controls instead of decorative elements
- Loading, empty, error, and disconnected states
- Keep the existing Nightwatch dashboard feel intact

## 16. Implementation principle
Build a single, coherent local incident lifecycle first: simulate services, detect failures, investigate them with evidence, approve a safe remediation, verify recovery, and persist the full result.

## 17. Final acceptance requirement
The completed application must be a working integrated prototype, not a static mock or placeholder dashboard. It must show an end-to-end incident lifecycle with real simulation, real backend logic, and persistent reporting.
