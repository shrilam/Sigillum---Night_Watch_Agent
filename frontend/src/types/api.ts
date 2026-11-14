export type ServiceStatus = "healthy" | "degraded" | "critical";
export type Severity = "Critical" | "High" | "Medium" | "Low";

export interface Service {
  id: string;
  name: string;
  group: string;
  depends_on: string[];
  status: ServiceStatus;
}

export interface Incident {
  id: string;
  title: string;
  severity: Severity;
  status: string;
  trigger: string;
  impact: string;
  summary: string;
}

export interface SimulatorState {
  scenario_id: string;
  incident: Incident;
  elapsed_minutes: number;
  services: Service[];
  resolved: boolean;
}
