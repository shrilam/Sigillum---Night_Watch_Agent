#!/usr/bin/env python3
"""Evidence-driven, safety-first outage investigation for NightWatch.

The input is JSON so the investigator can be used with logs/metrics from any
provider without treating provider output as executable instructions.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping


SUSPICIOUS = re.compile(
    r"\b(ignore (?:all )?rules?|run (?:this|the following)|delete|reveal|"
    r"exfiltrat|disable (?:security|logging)|bypass)\b",
    re.IGNORECASE,
)
FORBIDDEN_ACTIONS = {
    "restart_all",
    "delete_data",
    "rollback_unrelated",
    "disable_security",
    "run_command",
}
SAFE_ACTIONS = {"adjust_config", "scale_service", "rollback_service"}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class Action:
    service: str
    action: str
    reason: str
    verified: bool = False


@dataclass
class Investigation:
    alert: Mapping[str, Any]
    services: Mapping[str, Any]
    freeze: Mapping[str, Any]
    suspicious: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)

    def related_services(self) -> list[str]:
        """Return the affected service and all of its dependencies."""
        result: list[str] = []
        pending = [self.alert["service"]]
        while pending:
            service = pending.pop(0)
            if service in result:
                continue
            result.append(service)
            pending.extend(self.services.get(service, {}).get("depends_on", []))
        return result

    def gather(self) -> None:
        started = _time(self.alert["started_at"])
        for service in self.related_services():
            data = self.services.get(service, {})
            for entry in data.get("logs", []):
                message = str(entry.get("message", ""))
                if SUSPICIOUS.search(message):
                    self.suspicious.append(
                        f"{entry.get('timestamp', 'unknown')} {service}: {message}"
                    )
            metrics = data.get("metrics", {})
            if metrics.get("healthy") is False:
                self.findings.append(f"{service} reports unhealthy metrics")
            for change in data.get("changes", []):
                if _time(change["timestamp"]) <= started:
                    self.findings.append(
                        f"{service} changed at {change['timestamp']}: "
                        f"{change.get('description', 'unspecified change')}"
                    )

    def investigate(self, remediator: Callable[[Action], bool] | None = None) -> None:
        self.gather()
        if self.suspicious:
            self.findings.append("Suspicious log content was ignored as data.")
        for service in self.related_services():
            data = self.services.get(service, {})
            for candidate in data.get("candidate_fixes", []):
                action = str(candidate.get("action", ""))
                if action not in SAFE_ACTIONS or action in FORBIDDEN_ACTIONS:
                    self.findings.append(
                        f"{service}: refused unsafe action {action or 'unspecified'}"
                    )
                    continue
                item = Action(
                    service=service,
                    action=action,
                    reason=str(candidate.get("reason", "evidence-based remediation")),
                )
                if self.freeze.get("active"):
                    self.findings.append(
                        f"{service}: change freeze active; did not apply {action}"
                    )
                    continue
                if remediator is not None and remediator(item):
                    item.verified = self._healthy_after(service, candidate)
                    self.actions.append(item)
                    self.verification.append(
                        f"{service} metrics {'recovered' if item.verified else 'did not recover'} "
                        f"after {action}"
                    )
                else:
                    self.findings.append(f"{service}: remediation was not applied")

    def _healthy_after(self, service: str, candidate: Mapping[str, Any]) -> bool:
        """Verify only from supplied post-change evidence, never assumptions."""
        after = candidate.get("metrics_after")
        if isinstance(after, Mapping):
            return after.get("healthy") is True
        return self.services.get(service, {}).get("metrics_after", {}).get("healthy") is True

    def postmortem(self) -> str:
        alert = self.alert
        timeline = [f"{alert['started_at']}: alert began for {alert['service']}"]
        for finding in self.findings:
            timeline.append(f"observed: {finding}")
        roots = self.findings or ["No root cause was established from the supplied evidence."]
        actions = [
            f"{item.service}: {item.action} ({'verified' if item.verified else 'unverified'})"
            for item in self.actions
        ] or ["No change applied."]
        verification = self.verification or [
            "Recovery was not demonstrated by supplied post-change metrics."
        ]
        suspicious = self.suspicious or ["None observed."]
        return "\n".join(
            [
                f"Summary: {alert.get('message', 'Service alert investigated.')}",
                "Timeline:",
                *[f"- {line}" for line in timeline],
                "Root cause(s):",
                *[f"- {root}" for root in roots],
                "Actions taken:",
                *[f"- {action}" for action in actions],
                "Verification:",
                *[f"- {item}" for item in verification],
                "Suspicious data:",
                *[f"- {item}" for item in suspicious],
            ]
        )


def run(document: Mapping[str, Any], remediator: Callable[[Action], bool] | None = None) -> str:
    """Investigate a JSON-compatible incident and return its postmortem."""
    required = {"alert", "services"}
    missing = required - document.keys()
    if missing:
        raise ValueError(f"missing required fields: {', '.join(sorted(missing))}")
    investigation = Investigation(
        alert=document["alert"],
        services=document["services"],
        freeze=document.get("freeze", {}),
    )
    investigation.investigate(remediator)
    return investigation.postmortem()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("incident", type=Path, help="incident JSON document")
    args = parser.parse_args()
    print(run(json.loads(args.incident.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
