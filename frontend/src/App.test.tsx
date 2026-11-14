import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./services/api", () => ({
  getState: async () => ({
    scenario_id: "checkout-double-fault",
    incident: {
      id: "checkout-double-fault",
      title: "Checkout success rate dropped",
      severity: "Critical",
      status: "Investigating",
      trigger: "checkout-slo-burn",
      impact: "Checkout is degraded.",
      summary: "Synthetic seed incident.",
    },
    elapsed_minutes: 18,
    services: [],
    resolved: false,
  }),
  getServices: async () => [
    { id: "checkout", name: "Checkout", group: "Commerce", depends_on: [], status: "critical" },
  ],
}));

describe("App", () => {
  it("loads the seeded incident through the API client", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Checkout success rate dropped" })).toBeInTheDocument();
    expect(screen.getByText("LOCAL SIMULATOR")).toBeInTheDocument();
    expect(screen.getByText("Checkout")).toBeInTheDocument();
  });
});
