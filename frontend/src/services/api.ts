import type { Service, SimulatorState } from "../types/api";
import type {
  ActivityEvent,
  Evidence,
  IncidentReport,
  Investigation,
  MetricSample,
  ModelStatus,
  RemediationPlan,
  Scenario,
  Verification,
} from "../types/workflow";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getState = () => getJson<SimulatorState>("/api/state");
export const getServices = () => getJson<Service[]>("/api/services");
export const getScenarios = () => getJson<Scenario[]>("/api/scenarios");
export const getMetrics = (incidentId: string) => getJson<MetricSample[]>(`/api/metrics?incident_id=${encodeURIComponent(incidentId)}`);
export const getEvidence = (incidentId: string) => getJson<Evidence[]>(`/api/logs?incident_id=${encodeURIComponent(incidentId)}`);
export const getModelStatus = () => getJson<ModelStatus>("/api/model/status");
export const getEvents = (incidentId: string) => getJson<ActivityEvent[]>(`/api/events?incident_id=${encodeURIComponent(incidentId)}`);
export const getRemediations = (incidentId: string) => getJson<RemediationPlan[]>(`/api/remediation?incident_id=${encodeURIComponent(incidentId)}`);
export const injectScenario = (scenarioId: string) => postJson<SimulatorState>("/api/simulator/inject", { scenario_id: scenarioId });
export const investigate = (incidentId: string) => postJson<{ investigation: Investigation; remediations: RemediationPlan[] }>(`/api/incidents/${incidentId}/investigate`);
export const approveRemediation = (id: string, approver: string) => postJson<RemediationPlan>(`/api/remediation/${id}/approve`, { approved: true, approver });
export const executeRemediation = (id: string) => postJson<{ ok: boolean; state: SimulatorState }>(`/api/remediation/${id}/execute`);
export const verifyIncident = (incidentId: string) => postJson<Verification>(`/api/incidents/${incidentId}/verify`);
export const createReport = (incidentId: string, summary: string) => postJson<IncidentReport>(`/api/incidents/${incidentId}/report`, { summary });
