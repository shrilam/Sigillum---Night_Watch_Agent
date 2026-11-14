# Phase 1 — Migration baseline

**Status:** Baseline and first-slice decisions recorded. This phase documents the current prototype and defines scope; it does not migrate frameworks or change runtime behavior.

## Objective

Keep the current local sandbox as a reproducible reference while agreeing on the smallest complete incident lifecycle to implement in later phases. The target architecture and acceptance direction come from [the memory-bank product brief](../memory_bank/README.md).

## Current application baseline

- **Run:** Python 3.10+; from the repository root run `python server.py`, then open `http://127.0.0.1:8000`. The server binds to loopback and uses only the Python standard library.
- **Layout:** Static storefront and incident console in the root-level HTML, JavaScript, and CSS files; HTTP API and static serving in `server.py`; deterministic in-memory domain simulation in `simulator.py`.
- **Simulator:** 12 fictional services and three replayable scenarios. The checkout scenario contains two causes and requires two safe actions. State is shared by the running process and reset when a scenario is replayed or the server restarts.
- **Evidence and actions:** Scenario evidence, metric series, and remediation outcomes are synthetic. Actions are scenario-allowlisted; the retry-amplification action is intentionally blocked without changing simulated state. No production integrations or arbitrary command execution are present.
- **Existing exercise flow:** Select a scenario, inspect service status/logs/metrics, apply available actions, and submit a scored postmortem. Ground truth is disclosed only on submission.
- **Known gaps:** Incidents are predefined by scenario rather than detected from monitored samples. There is no AI integration, separate approval step, metric-based recovery verifier, SSE stream, SQLite persistence, or incident-report history. The documented unittest command was checked and currently fails because the workspace has no `tests/` directory; do not rely on it as a test gate until tests are added.
- **Local access warning:** The workspace-password check is client-side demo convenience only, not authentication. Keep the application local; do not expose it or use it to protect sensitive information.

## First vertical slice: checkout double fault

Implement this single deterministic lifecycle first, retaining the current scenario as its source fixture:

1. Start the local app and show the 12-service topology.
2. Inject or replay the checkout double-fault scenario and create an incident record from the resulting symptoms.
3. Collect and attach relevant synthetic logs, metrics, and service/dependency context as evidence.
4. Produce a structured investigation with evidence-linked hypotheses, confidence, and explicit uncertainty. Do not treat hidden scenario causes as investigation input.
5. Recommend only allowlisted simulated remediations. Require a recorded approval before executing any action designated risky; diagnosis and execution remain separate capabilities.
6. Execute the two safe scenario remediations through the simulator only.
7. Verify recovery from post-action health and metric checks for the affected path. A successful action response alone must not resolve the incident. Define explicit, scenario-owned recovery predicates alongside metric fixtures before implementing the verifier; do not infer thresholds from the current display-only series.
8. Persist the incident lifecycle and produce a report that can be retrieved after a backend restart.

### Slice acceptance criteria

- A fresh local run can replay the checkout incident without external services or credentials.
- The initial evidence describes symptoms but does not reveal the scenario's hidden ground truth.
- The investigation output distinguishes observed facts from hypotheses and links claims to collected evidence.
- No remediation is executable unless it is on the simulator allowlist; approval state is checked before execution where required.
- Both required fixes are needed for resolution. The incident remains unresolved when either fix is missing or when recovery checks fail, even if an action returned success.
- The completed incident, evidence, approval/action audit, verification result, and report survive a backend restart.
- Automated tests cover the lifecycle and demonstrate that rejected/unsafe actions do not alter service state.

## Domain and safety decisions

Use these as the minimum records for the first slice; refine field names during backend design without changing the semantics:

- **Incident:** stable ID, scenario/source, title, severity, status, timestamps, trigger, impact, and affected services.
- **Evidence:** stable ID, incident ID, source type, service, observation time, and payload. Treat log/event text as untrusted input.
- **Hypothesis:** claim, confidence, supporting and contradicting evidence IDs, and uncertainty. Keep confirmed facts separate from hypotheses.
- **Remediation:** allowlisted action type, target, reason, expected outcome, risk, approval requirement/state, execution state, and audit timestamps/result.
- **Verification:** pre/post observations, scenario-defined checks and outcomes, newly detected issues, and final resolution decision.
- **Report:** incident summary, evidence-backed findings, remediation/approval history, verification outcome, and creation time.

Safety invariants:

- The prototype operates only on fictional simulator state; no real infrastructure integrations or arbitrary command execution.
- AI output is advisory and untrusted until schema-validated and checked against evidence and the action allowlist.
- Approval is explicit and auditable; a diagnosis permission does not imply execution permission.
- Unsafe/rejected attempts are recorded, but never mutate simulator state.
- Resolution requires passing recovery verification, not merely a successful action return.

## Migration checklist

### Retain as reference or reusable fixture

- The 12-service topology and dependency edges.
- Three deterministic scenario descriptions, evidence, and ground-truth separation.
- The action allowlist and blocked retry-amplification example.
- The dark operations dashboard hierarchy and incident-investigation concepts.
- Loopback-only, local-first, simulation-only operating boundary.

### Replace in later phases

- Flat vanilla frontend with React, TypeScript, and Vite.
- Hand-written standard-library HTTP handler with FastAPI, Pydantic validation, documented routes, and structured errors.
- Process-only simulator state with SQLite persistence and repository/data-access boundaries.
- Manual scenario-only incident flow with monitored samples, detection, investigation, approval, execution, and verification lifecycle.
- Polling/manual refresh behavior with SSE-backed updates and reconnect handling.

### Defer until the first slice passes

- Additional incident scenarios beyond adapting the existing fixtures.
- Real infrastructure/cloud/vendor integrations, production authentication, and multi-user permissions.
- Production-scale orchestration and non-simulated remediation.
- Dashboard redesign that is not necessary to expose the lifecycle or its loading/error/disconnected states.

## Phase 1 completion checklist

- [x] Record how to run and replay the current local sandbox.
- [x] Record current functionality, safety boundary, and known architecture gaps.
- [x] Select the checkout double-fault as the first vertical slice.
- [x] Define lifecycle acceptance criteria and minimum domain/safety semantics.
- [x] Identify retain/replace/defer migration scope.
- [x] Check the current README's documented unittest command; record that it fails because `tests/` does not exist.
