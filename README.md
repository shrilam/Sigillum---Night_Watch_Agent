# Sigillum---Night_Watch_Agent
NightWatch: an AI on-call agent that investigates outages, finds the real root cause, applies safe fixes, and writes the postmortem. Built for the Studentpreneurs Buildathon.

## Usage

NightWatch consumes a JSON incident document containing an `alert` and a
`services` map. Each service may provide `depends_on`, `logs`, `metrics`,
`changes`, and evidence-backed `candidate_fixes`. Logs are treated as
untrusted data; changes are skipped while `freeze.active` is true.

```sh
python nightwatch.py incident.json
python -m unittest -v
```

Candidate fixes are only passed to a caller-provided remediator when they are
allowlisted (`adjust_config`, `scale_service`, or `rollback_service`). The
remediator must return success, and the incident must include post-change
healthy metrics for the action to be reported as verified.
