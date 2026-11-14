export interface Scenario {
  id: string;
  title: string;
  severity: string;
  summary: string;
}

export interface MetricSample {
  service_id: string;
  name: string;
  value: number;
  unit: string;
  threshold: number;
  operator: "gt" | "gte" | "lt" | "lte";
  breach_severity: string;
  observed_at: string;
}

export interface Evidence {
  id: string;
  incident_id: string;
  service_id: string;
  level: "info" | "warning" | "error";
  message: string;
  observed_at: string;
  source: string;
}

export interface Hypothesis {
  id: string;
  statement: string;
  confidence: number;
  evidence_ids: string[];
  caveat: string;
}

export interface Investigation {
  incident_id: string;
  provider: string;
  summary: string;
  facts: string[];
  hypotheses: Hypothesis[];
  created_at: string;
}

export interface RemediationPlan {
  id: string;
  incident_id: string;
  action_id: string;
  title: string;
  description: string;
  target_service: string;
  reason: string;
  expected_outcome: string;
  risk: "low" | "medium" | "high";
  approval_required: boolean;
  approved: boolean;
  approved_by?: string | null;
  approval_at?: string | null;
  status: "pending_approval" | "approved" | "executed" | "blocked";
  created_at: string;
  executed_at?: string | null;
}

export interface VerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Verification {
  id: string;
  incident_id: string;
  passed: boolean;
  resolved: boolean;
  checks: VerificationCheck[];
  created_at: string;
}

export interface IncidentReport {
  id: string;
  incident_id: string;
  title: string;
  summary: string;
  findings: string[];
  evidence_ids: string[];
  actions: string[];
  verification?: Verification | null;
  created_at: string;
}

export interface ModelStatus {
  available: boolean;
  model: string;
  models: string[];
  error: string | null;
}

export interface ActivityEvent {
  id: string;
  incident_id: string;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}
