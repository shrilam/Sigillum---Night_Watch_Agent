"""Public, deterministic simulator fixtures. No hidden ground truth is stored here."""

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
        "id": "checkout-double-fault",
        "title": "Checkout success rate dropped",
        "trigger": "checkout-slo-burn",
        "impact": "Customers may be unable to place orders; inventory availability may be inaccurate.",
        "elapsed_minutes": 18,
        "summary": "Checkout completions fell sharply while payment and inventory signals degraded.",
        "severity": "Critical",
        "service_status": {"checkout": "critical", "payments": "critical", "inventory": "degraded", "orders": "degraded", "api-gateway": "degraded"},
        "metrics": [
            {"service_id": "checkout", "name": "success_rate", "value": 22, "unit": "%", "threshold": 90, "operator": "lt", "breach_severity": "Critical"},
            {"service_id": "payments", "name": "connection_pool_usage", "value": 100, "unit": "%", "threshold": 85, "operator": "gt", "breach_severity": "Critical"},
            {"service_id": "inventory", "name": "stale_read_rate", "value": 91, "unit": "%", "threshold": 5, "operator": "gt", "breach_severity": "High"},
            {"service_id": "api-gateway", "name": "checkout_p95_latency", "value": 640, "unit": "ms", "threshold": 500, "operator": "gt", "breach_severity": "High"},
        ],
        "actions": ["drain-payment-workers", "refresh-inventory-cache"],
        "action_options": ["drain-payment-workers", "refresh-inventory-cache", "increase-checkout-retries"],
        "evidence": [
            ("payments", "error", "connection pool at 100%; acquire timeout exceeded"),
            ("checkout", "error", "payment authorization timed out after 3000ms"),
            ("inventory", "warning", "cache revision 884 behind source revision 901"),
            ("cart", "warning", "availability check returned stale revision 884"),
            ("orders", "warning", "order creation retries elevated; duplicate guard active"),
            ("api-gateway", "info", "checkout route p95 latency 4.8s (threshold 1.0s)"),
        ],
    },
    "catalog-hot-partition": {
        "id": "catalog-hot-partition",
        "title": "Product detail latency elevated",
        "trigger": "catalog-latency-slo",
        "impact": "Customers may see slow product pages and search results.",
        "elapsed_minutes": 31,
        "summary": "Product detail requests are slow, while checkout remains mostly healthy.",
        "severity": "High",
        "service_status": {"catalog": "critical", "storefront": "degraded", "api-gateway": "degraded"},
        "metrics": [
            {"service_id": "catalog", "name": "p95_latency", "value": 870, "unit": "ms", "threshold": 500, "operator": "gt", "breach_severity": "Critical"},
            {"service_id": "catalog", "name": "partition_concentration", "value": 86, "unit": "%", "threshold": 75, "operator": "gt", "breach_severity": "High"},
            {"service_id": "checkout", "name": "success_rate", "value": 97, "unit": "%", "threshold": 90, "operator": "lt", "breach_severity": "Critical"},
        ],
        "actions": ["rebalance-catalog-index"],
        "action_options": ["rebalance-catalog-index", "increase-checkout-retries"],
        "evidence": [
            ("catalog", "error", "partition p-17 read latency 1820ms; other partitions under 40ms"),
            ("catalog", "warning", "request concentration on partition p-17 reached 86%"),
            ("storefront", "warning", "product route p95 latency 2.4s"),
            ("checkout", "info", "checkout success rate stable at 97.8%"),
            ("api-gateway", "info", "product route retries within normal range"),
        ],
    },
    "notification-lag": {
        "id": "notification-lag",
        "title": "Order notification queue growing",
        "trigger": "notification-queue-depth",
        "impact": "Customers may not receive confirmation messages promptly.",
        "elapsed_minutes": 24,
        "summary": "Order confirmation messages are delayed; order placement is unaffected.",
        "severity": "High",
        "service_status": {"notifications": "critical", "orders": "degraded"},
        "metrics": [
            {"service_id": "notifications", "name": "queue_depth", "value": 18420, "unit": "messages", "threshold": 10000, "operator": "gt", "breach_severity": "High"},
            {"service_id": "notifications", "name": "active_consumers", "value": 2, "unit": "consumers", "threshold": 4, "operator": "lt", "breach_severity": "High"},
            {"service_id": "orders", "name": "write_success_rate", "value": 99, "unit": "%", "threshold": 95, "operator": "lt", "breach_severity": "Critical"},
        ],
        "actions": ["scale-notification-consumers"],
        "action_options": ["scale-notification-consumers", "increase-checkout-retries"],
        "evidence": [
            ("notifications", "error", "consumer group lag 18,420 messages; oldest message 14m"),
            ("notifications", "warning", "active consumers 2 of desired 8"),
            ("orders", "info", "order write success rate 99.4%"),
            ("shipping", "info", "fulfillment events arriving within 30s"),
            ("notifications", "warning", "delivery latency p95 11m 32s"),
        ],
    },
}

ACTION_CATALOG = {
    "drain-payment-workers": {
        "title": "Drain & replace payment workers",
        "description": "Recycle workers holding open payment connections inside the simulator.",
        "target_service": "payments",
        "reason": "Payment connection-pool usage is above its configured threshold.",
        "expected_outcome": "Payment pool usage falls below threshold and checkout succeeds.",
        "risk": "low",
        "approval_required": False,
    },
    "refresh-inventory-cache": {
        "title": "Refresh inventory cache",
        "description": "Refresh the synthetic inventory cache from its source revision.",
        "target_service": "inventory",
        "reason": "Inventory telemetry reports stale reads above threshold.",
        "expected_outcome": "Stale inventory reads return below threshold.",
        "risk": "low",
        "approval_required": False,
    },
    "rebalance-catalog-index": {
        "title": "Rebalance catalog partition",
        "description": "Move the simulated hot catalog partition and distribute reads.",
        "target_service": "catalog",
        "reason": "Catalog p95 latency and partition concentration exceed thresholds.",
        "expected_outcome": "Catalog latency and partition concentration return below thresholds.",
        "risk": "medium",
        "approval_required": True,
    },
    "scale-notification-consumers": {
        "title": "Scale notification consumers",
        "description": "Restore the synthetic notification consumer group to target capacity.",
        "target_service": "notifications",
        "reason": "Queue depth is high and active consumers are below target.",
        "expected_outcome": "Queue depth drains and consumer capacity meets target.",
        "risk": "low",
        "approval_required": False,
    },
    "increase-checkout-retries": {
        "title": "Increase checkout retries",
        "description": "Unsafe: adds load to already degraded dependencies.",
        "target_service": "checkout",
        "reason": "Rejected unsafe retry amplification option.",
        "expected_outcome": "No state change; action is blocked.",
        "risk": "high",
        "approval_required": True,
        "unsafe": True,
    },
}

SCENARIO_SUMMARIES = [
    {
        "id": scenario["id"],
        "title": scenario["title"],
        "severity": scenario["severity"],
        "summary": scenario["summary"],
    }
    for scenario in SCENARIOS.values()
]
