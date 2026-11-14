import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./services/api", () => ({
  getState: async () => ({
    scenario_id: "checkout-double-fault",
    incident: {
      id: "checkout-double-fault",
      scenario_id: "checkout-double-fault",
      title: "Checkout success rate dropped",
      severity: "Critical",
      status: "Investigating",
      trigger: "checkout-slo-burn",
      impact: "Checkout is degraded.",
      summary: "Synthetic seed incident.",
      affected_services: ["checkout"],
      created_at: "2026-11-14T00:00:00Z",
      updated_at: "2026-11-14T00:00:00Z",
    },
    elapsed_minutes: 18,
    services: [],
    resolved: false,
  }),
  getServices: async () => [
    { id: "checkout", name: "Checkout", group: "Commerce", depends_on: [], status: "critical" },
  ],
  getScenarios: async () => [{ id: "checkout-double-fault", title: "Checkout success rate dropped", severity: "Critical", summary: "Synthetic seed incident." }],
  getModelStatus: async () => ({ available: false, model: "qwen2.5-coder:7b", models: [], error: "offline" }),
  getMetrics: async () => [],
  getEvidence: async () => [],
  getRemediations: async () => [],
  getEvents: async () => [],
}));

describe("App", () => {
  it("loads the seeded incident through the API client", async () => {
    vi.stubGlobal("EventSource", class {
      onopen: (() => void) | null = null;
      onerror: (() => void) | null = null;
      addEventListener() {}
      removeEventListener() {}
      close() {}
    });
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Checkout success rate dropped" })).toBeInTheDocument();
    expect(screen.getByText("LOCAL SIMULATOR")).toBeInTheDocument();
    expect(screen.getByText("Checkout")).toBeInTheDocument();
  });
});
