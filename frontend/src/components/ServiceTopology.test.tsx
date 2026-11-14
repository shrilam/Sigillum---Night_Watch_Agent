import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ServiceTopology } from "./ServiceTopology";
import type { Service } from "../types/api";

const services: Service[] = [
  { id: "checkout", name: "Checkout", group: "Commerce", depends_on: ["payments"], status: "critical" },
  { id: "payments", name: "Payments", group: "Fulfillment", depends_on: [], status: "degraded" },
];

describe("ServiceTopology", () => {
  it("renders service groups and health states", () => {
    render(<ServiceTopology services={services} />);

    expect(screen.getByRole("heading", { name: "Service topology" })).toBeInTheDocument();
    expect(screen.getByText("Checkout")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("Payments")).toBeInTheDocument();
    expect(screen.getByText("degraded")).toBeInTheDocument();
  });
});
