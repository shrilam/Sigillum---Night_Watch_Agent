"""Seed fixtures ported from the original local-only simulator.

These are public demo symptoms only. Hidden scenario causes are deliberately
not included in API responses or frontend data.
"""

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

CHECKOUT_SCENARIO = {
    "id": "checkout-double-fault",
    "title": "Checkout success rate dropped",
    "severity": "Critical",
    "status": "Investigating",
    "trigger": "checkout-slo-burn",
    "impact": "Customers may be unable to place orders; inventory availability may be inaccurate.",
    "elapsed_minutes": 18,
    "summary": "Checkout completions fell sharply while payment and inventory signals degraded.",
    "service_status": {
        "checkout": "critical",
        "payments": "critical",
        "inventory": "degraded",
        "orders": "degraded",
        "api-gateway": "degraded",
    },
}

SCENARIOS = [
    {
        "id": CHECKOUT_SCENARIO["id"],
        "title": CHECKOUT_SCENARIO["title"],
        "severity": CHECKOUT_SCENARIO["severity"],
        "summary": CHECKOUT_SCENARIO["summary"],
    }
]
