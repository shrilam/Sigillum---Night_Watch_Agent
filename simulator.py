"""Deterministic, local-only incident simulator for the On-call Lab."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock


SERVICES = [
    {"id": "storefront", "name": "Storefront", "group": "Edge", "depends_on": ["api-gateway", "catalog", "cart"]},
    {"id": "api-gateway", "name": "API Gateway", "group": "Edge", "depends_on": ["identity", "catalog", "cart", "checkout"]},
    {"id": "identity", "name": "Identity", "group": "Core", "depends_on": []},
    {"id": "catalog", "name": "Catalog", "group": "Commerce", "depends_on": ["pricing"]},
    {"id": "cart", "name": "Cart", "group": "Commerce", "depends_on": ["pricing", "inventory"]},
    {"id": "pricing", "name": "Pricing", "group": "Commerce", "depends_on": []},
    {"id": "inventory", "name": "Inventory", "group": "Commerce", "depends_on": []},
    {"id": "checkout", "name": "Checkout", "group": "Commerce", "depends_on": ["inventory", "payments", "orders"]},
    {"id": "payments", "name": "Payments", "group": "Fulfillment", "depends_on": []},
    {"id": "orders", "name": "Orders", "group": "Fulfillment", "depends_on": []},
    {"id": "shipping", "name": "Shipping", "group": "Fulfillment", "depends_on": ["orders"]},
    {"id": "notifications", "name": "Notifications", "group": "Fulfillment", "depends_on": ["orders"]},
]

SCENARIOS = {
    "checkout-double-fault": {
        "title": "Checkout success rate dropped",
        "severity": "SEV-1",
        "trigger": "checkout-slo-burn",
        "status": "Investigating",
        "started_minutes_ago": 18,
        "summary": "Checkout completions fell sharply while payment and inventory signals degraded.",
        "impact": "Customers may be unable to place orders; inventory availability may be inaccurate.",
        "services": {"checkout": "critical", "payments": "critical", "inventory": "degraded", "orders": "degraded", "api-gateway": "degraded"},
        "causes": ["payment_pool_exhaustion", "inventory_cache_staleness"],
        "actions": ["drain-payment-workers", "refresh-inventory-cache"],
        "action_options": ["drain-payment-workers", "refresh-inventory-cache", "increase-checkout-retries"],
        "diagnostics": ["payment_pool_exhaustion", "inventory_cache_staleness", "catalog_hot_partition", "notification_consumer_lag", "gateway_rate_limit_misconfiguration"],
        "evidence": [
            ("payments", "error", "connection pool at 100%; acquire timeout exceeded"),
            ("checkout", "error", "payment authorization timed out after 3000ms"),
            ("inventory", "warning", "cache revision 884 behind source revision 901"),
            ("cart", "warning", "availability check returned stale revision 884"),
            ("orders", "warning", "order creation retries elevated; duplicate guard active"),
            ("api-gateway", "info", "checkout route p95 latency 4.8s (threshold 1.0s)"),
            ("payments", "warning", "worker checkout-pay-7 recycled with 42 open connections"),
        ],
        "metrics": {"checkout": (98, 22, "success %"), "payments": (120, 14, "requests/s"), "inventory": (42, 91, "stale reads %"), "orders": (96, 58, "success %"), "api-gateway": (180, 640, "p95 ms")},
    },
    "catalog-hot-partition": {
        "title": "Product detail latency elevated",
        "severity": "SEV-2",
        "trigger": "catalog-latency-slo",
        "status": "Investigating",
        "started_minutes_ago": 31,
        "summary": "Product detail requests are slow, while checkout remains mostly healthy.",
        "impact": "Customers may see slow product pages and search results.",
        "services": {"catalog": "critical", "storefront": "degraded", "api-gateway": "degraded"},
        "causes": ["catalog_hot_partition"],
        "actions": ["rebalance-catalog-index"],
        "action_options": ["rebalance-catalog-index", "increase-checkout-retries"],
        "diagnostics": ["payment_pool_exhaustion", "inventory_cache_staleness", "catalog_hot_partition", "notification_consumer_lag", "gateway_rate_limit_misconfiguration"],
        "evidence": [
            ("catalog", "error", "partition p-17 read latency 1820ms; other partitions under 40ms"),
            ("catalog", "warning", "request concentration on partition p-17 reached 86%"),
            ("storefront", "warning", "product route p95 latency 2.4s"),
            ("checkout", "info", "checkout success rate stable at 97.8%"),
            ("api-gateway", "info", "product route retries within normal range"),
        ],
        "metrics": {"catalog": (45, 870, "p95 ms"), "storefront": (160, 520, "p95 ms"), "api-gateway": (220, 390, "p95 ms"), "checkout": (98, 97, "success %")},
    },
    "notification-lag": {
        "title": "Order notification queue growing",
        "severity": "SEV-2",
        "trigger": "notification-queue-depth",
        "status": "Investigating",
        "started_minutes_ago": 24,
        "summary": "Order confirmation messages are delayed; order placement is unaffected.",
        "impact": "Customers may not receive confirmation messages promptly.",
        "services": {"notifications": "critical", "orders": "degraded"},
        "causes": ["notification_consumer_lag"],
        "actions": ["scale-notification-consumers"],
        "action_options": ["scale-notification-consumers", "increase-checkout-retries"],
        "diagnostics": ["payment_pool_exhaustion", "inventory_cache_staleness", "catalog_hot_partition", "notification_consumer_lag", "gateway_rate_limit_misconfiguration"],
        "evidence": [
            ("notifications", "error", "consumer group lag 18,420 messages; oldest message 14m"),
            ("notifications", "warning", "active consumers 2 of desired 8"),
            ("orders", "info", "order write success rate 99.4%"),
            ("shipping", "info", "fulfillment events arriving within 30s"),
            ("notifications", "warning", "delivery latency p95 11m 32s"),
        ],
        "metrics": {"notifications": (120, 18420, "queue depth"), "orders": (99, 99, "success %"), "shipping": (35, 38, "p95 s")},
    },
}

CAUSE_CATALOG = {
    "payment_pool_exhaustion": "Payment worker connection pool exhausted by unreleased connections",
    "inventory_cache_staleness": "Inventory cache stopped refreshing and served stale availability",
    "catalog_hot_partition": "Catalog traffic concentrated on a hot database partition",
    "notification_consumer_lag": "Notification consumer capacity fell below incoming message volume",
    "gateway_rate_limit_misconfiguration": "Gateway rate limit was configured too aggressively",
}

ACTION_CATALOG = {
    "drain-payment-workers": {"label": "Drain & replace payment workers", "description": "Replace workers holding leaked connections; payment pool recovers.", "service": "payments"},
    "refresh-inventory-cache": {"label": "Refresh inventory cache", "description": "Rebuild the stale cache from the inventory source of truth.", "service": "inventory"},
    "rebalance-catalog-index": {"label": "Rebalance catalog partition", "description": "Move the hot catalog shard and spread read traffic.", "service": "catalog"},
    "scale-notification-consumers": {"label": "Scale notification consumers", "description": "Restore the consumer group to its desired capacity.", "service": "notifications"},
    "increase-checkout-retries": {"label": "Increase checkout retries", "description": "Unsafe: adds load to already degraded dependencies.", "service": "checkout", "unsafe": True},
}


class Simulator:
    def __init__(self) -> None:
        self.lock = RLock()
        self.reset("checkout-double-fault")

    def reset(self, scenario_id: str) -> dict:
        if scenario_id not in SCENARIOS:
            raise ValueError("Unknown scenario")
        with self.lock:
            self.scenario_id = scenario_id
            self.fixed: set[str] = set()
            self.actions_taken: list[dict] = []
            self.closed = False
            self.submission: dict | None = None
            self.started_at = datetime.now(timezone.utc)
            return self.state()

    def state(self) -> dict:
        with self.lock:
            scenario = SCENARIOS[self.scenario_id]
            service_status = {service["id"]: "healthy" for service in SERVICES}
            service_status.update(scenario["services"])
            for action_id in self.fixed:
                action = ACTION_CATALOG[action_id]
                service_status[action["service"]] = "healthy"
            # A service is resolved only when all of its own causal conditions are fixed.
            for service_id in service_status:
                service_causes = [cause for cause in scenario["causes"] if ACTION_CATALOG[scenario["actions"][scenario["causes"].index(cause)]] ["service"] == service_id]
                if service_causes and all(scenario["actions"][scenario["causes"].index(cause)] in self.fixed for cause in service_causes):
                    service_status[service_id] = "healthy"
            all_fixed = set(scenario["actions"]).issubset(self.fixed)
            if all_fixed:
                for service_id in scenario["services"]:
                    service_status[service_id] = "healthy"
            return {
                "scenario_id": self.scenario_id,
                "incident": {key: scenario[key] for key in ("title", "severity", "impact", "trigger")},
                "elapsed_minutes": max(1, int((datetime.now(timezone.utc) - self.started_at).total_seconds() // 60) + scenario["started_minutes_ago"]),
                "services": [{**service, "status": service_status[service["id"]]} for service in SERVICES],
                "fixed_actions": sorted(self.fixed),
                "actions_taken": list(self.actions_taken),
                "resolved": all_fixed,
                "closed": self.closed,
            }

    def scenarios(self) -> list[dict]:
        return [{"id": key, "title": value["title"], "severity": value["severity"], "summary": value["summary"]} for key, value in SCENARIOS.items()]

    def logs(self, service_id: str | None = None, query: str = "") -> list[dict]:
        with self.lock:
            scenario = SCENARIOS[self.scenario_id]
            now = datetime.now(timezone.utc)
            rows = []
            for index, (service, level, message) in enumerate(scenario["evidence"]):
                rows.append({"time": (now - timedelta(minutes=17, seconds=index * 19)).isoformat(), "service": service, "level": level, "message": message})
            for index, event in enumerate(self.actions_taken):
                rows.append({"time": event["time"], "service": event["service"], "level": event["level"], "message": event["message"]})
            if self.submission:
                rows.append({"time": self.submission["time"], "service": "on-call-lab", "level": "info", "message": "Postmortem submitted; evaluation recorded."})
            if service_id:
                rows = [row for row in rows if row["service"] == service_id]
            needle = query.lower().strip()
            if needle:
                rows = [row for row in rows if needle in (row["message"] + row["service"] + row["level"]).lower()]
            return sorted(rows, key=lambda row: row["time"], reverse=True)

    def metrics(self, service_id: str | None = None) -> dict:
        scenario = SCENARIOS[self.scenario_id]
        ids = [service_id] if service_id in scenario["metrics"] else list(scenario["metrics"])
        result = []
        for sid in ids:
            before, during, unit = scenario["metrics"][sid]
            affected = any(ACTION_CATALOG[action]["service"] == sid for action in scenario["actions"])
            recovered = affected and all(action in self.fixed for action in scenario["actions"] if ACTION_CATALOG[action]["service"] == sid)
            values = [before, before, int(before * 0.97), int(before * 0.78), int(during * 1.05), during, int(during * 0.99), int(before * 0.45 + during * 0.55), before] if recovered else [before, before, int(before * 0.98), int(before * 0.86), int(before * 0.7 + during * 0.3), int(before * 0.35 + during * 0.65), during, int(during * 1.02), int(during * 0.99)]
            result.append({"service": sid, "unit": unit, "values": values})
        return {"series": result, "labels": ["-40m", "-35m", "-30m", "-25m", "-20m", "-15m", "-10m", "-5m", "now"]}

    def available_actions(self) -> list[dict]:
        return [{"id": action, **ACTION_CATALOG[action]} for action in SCENARIOS[self.scenario_id]["action_options"]]

    def remediate(self, action_id: str) -> dict:
        with self.lock:
            scenario = SCENARIOS[self.scenario_id]
            if action_id not in ACTION_CATALOG or action_id not in scenario["action_options"]:
                self.actions_taken.append({"time": datetime.now(timezone.utc).isoformat(), "service": "on-call-lab", "level": "warning", "message": f"Rejected unknown or unavailable action: {action_id}"})
                raise ValueError("Action is not allowlisted for this incident")
            action = ACTION_CATALOG[action_id]
            if action.get("unsafe"):
                self.actions_taken.append({"time": datetime.now(timezone.utc).isoformat(), "service": action["service"], "level": "warning", "message": "Blocked unsafe retry increase: would amplify load on degraded dependencies."})
                return {"ok": False, "safe": False, "message": "Blocked: retry amplification would add load to a degraded checkout path. No simulated state changed."}
            if action_id in self.fixed:
                return {"ok": True, "safe": True, "message": "This remediation is already applied."}
            self.fixed.add(action_id)
            message = f"Applied remediation: {action['label']}. Health signals are recovering."
            self.actions_taken.append({"time": datetime.now(timezone.utc).isoformat(), "service": action["service"], "level": "info", "message": message})
            return {"ok": True, "safe": True, "message": message, "state": self.state()}

    def submit(self, summary: str, cause_ids: list[str]) -> dict:
        with self.lock:
            scenario = SCENARIOS[self.scenario_id]
            found = set(cause_ids) & set(CAUSE_CATALOG)
            actual = set(scenario["causes"])
            missing = sorted(actual - found)
            incorrect = sorted(found - actual)
            all_fixed = set(scenario["actions"]).issubset(self.fixed)
            summary_ok = len(summary.strip()) >= 40
            recall = len(actual & found) / max(1, len(actual))
            precision = len(actual & found) / max(1, len(found))
            diagnosis_score = round(60 * recall + 40 * precision)
            remediation_score = 100 if all_fixed else round(100 * len(set(scenario["actions"]) & self.fixed) / len(scenario["actions"]))
            postmortem_score = 100 if summary_ok and not missing and not incorrect else (70 if summary_ok else 0)
            total = round(diagnosis_score * 0.5 + remediation_score * 0.3 + postmortem_score * 0.2)
            resolved = not missing and all_fixed
            self.closed = resolved
            result = {
                "score": total,
                "diagnosis_score": diagnosis_score,
                "remediation_score": remediation_score,
                "postmortem_score": postmortem_score,
                "resolved": resolved,
                "summary_valid": summary_ok,
                "missing_causes": missing,
                "incorrect_causes": incorrect,
                "causes_found": sorted(found),
                "ground_truth": [{"id": cause, "description": CAUSE_CATALOG[cause]} for cause in scenario["causes"]],
                "fixes_complete": all_fixed,
                "message": "Incident resolved — all causes identified and mitigations applied." if resolved else "Review the uncovered causes and incomplete remediations, then continue investigating.",
            }
            self.submission = {"time": datetime.now(timezone.utc).isoformat(), "result": result}
            return result


SIMULATOR = Simulator()