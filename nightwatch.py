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


def _safe(value: Any) -> str:
    """Keep provider-controlled text from changing the report structure."""
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).strip()


def _validate(document: Mapping[str, Any]) -> None:
    if not isinstance(document, Mapping) or not isinstance(document.get("alert"), Mapping):
        raise ValueError("incident must contain an alert object")
    alert = document["alert"]
    if not isinstance(alert.get("service"), str) or not isinstance(
        alert.get("started_at"), str
    ):
        raise ValueError("alert requires service and started_at strings")
    try:
        _time(alert["started_at"])
    except (TypeError, ValueError) as exc:
        raise ValueError("alert.started_at must be an ISO-8601 timestamp") from exc
    if not isinstance(document.get("services"), Mapping):
        raise ValueError("incident must contain a services object")
    for service, data in document["services"].items():
        if not isinstance(data, Mapping):
            raise ValueError(f"service {service!r} must be an object")
        for key in ("depends_on", "logs", "changes"):
            if key in data and not isinstance(data[key], list):
                raise ValueError(f"{service}.{key} must be a list")
        for change in data.get("changes", []):
            if not isinstance(change, Mapping) or not isinstance(
                change.get("timestamp"), str
            ):
                raise ValueError(f"{service}.changes entries require timestamp")
            try:
                _time(change["timestamp"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{service}.changes timestamp is invalid") from exc


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
                        f"{_safe(entry.get('timestamp', 'unknown'))} {service}: {_safe(message)}"
                    )
            metrics = data.get("metrics", {})
            if metrics.get("healthy") is False:
                self.findings.append(f"{service} reports unhealthy metrics")
            for change in data.get("changes", []):
                if _time(change["timestamp"]) <= started:
                    self.findings.append(
                        f"{service} changed at {_safe(change['timestamp'])}: "
                        f"{_safe(change.get('description', 'unspecified change'))}"
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
        roots = [
            finding for finding in self.findings if "changed at" in finding
        ] or ["No root cause was established from the supplied evidence."]
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
                f"Summary: {_safe(alert.get('message', 'Service alert investigated.'))}",
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
    _validate(document)
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
