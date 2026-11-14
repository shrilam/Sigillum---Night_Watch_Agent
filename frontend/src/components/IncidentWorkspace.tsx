import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Check, CircleAlert, FileText, FlaskConical, RefreshCw, Search, ShieldCheck, Sparkles } from "lucide-react";
import { approveRemediation, createReport, executeRemediation, getEvidence, getEvents, getMetrics, getModelStatus, getRemediations, getScenarios, injectScenario, investigate, verifyIncident } from "../services/api";
import type { Incident } from "../types/api";
import type { ActivityEvent, Evidence, IncidentReport, Investigation, MetricSample, ModelStatus, RemediationPlan, Scenario, Verification } from "../types/workflow";
import "./IncidentWorkspace.css";

interface IncidentWorkspaceProps {
  incident: Incident;
  onRefresh: () => void;
}

const eventLabels: Record<string, string> = {
  "scenario.injected": "Scenario injected",
  "incident.detected": "Incident detected",
  "investigation.completed": "Investigation completed",
  "remediation.approved": "Remediation approved",
  "remediation.rejected": "Remediation rejected",
  "remediation.executed": "Simulated remediation executed",
  "recovery.verified": "Recovery verification completed",
  "report.created": "Incident report generated",
};

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function IncidentWorkspace({ incident, onRefresh }: IncidentWorkspaceProps) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState(incident.scenario_id);
  const [metrics, setMetrics] = useState<MetricSample[]>([]);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [plans, setPlans] = useState<RemediationPlan[]>([]);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [report, setReport] = useState<IncidentReport | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [streamConnected, setStreamConnected] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [reportSummary, setReportSummary] = useState("");
  const [serviceFilter, setServiceFilter] = useState("all");
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const activeIncidentId = useRef(incident.id);
  activeIncidentId.current = incident.id;

  const refreshDetails = useCallback(async () => {
    const targetIncidentId = incident.id;
    try {
      const [nextMetrics, nextEvidence, nextPlans, nextEvents] = await Promise.all([
        getMetrics(targetIncidentId), getEvidence(targetIncidentId), getRemediations(targetIncidentId), getEvents(targetIncidentId),
      ]);
      if (activeIncidentId.current !== targetIncidentId) return;
      setMetrics(nextMetrics);
      setEvidence(nextEvidence);
      setPlans(nextPlans);
      setEvents(nextEvents);
    } catch (cause) {
      if (activeIncidentId.current !== targetIncidentId) return;
      setError(cause instanceof Error ? cause.message : "Could not load incident evidence.");
    }
  }, [incident.id]);

  useEffect(() => {
    let active = true;
    setScenarioId(incident.scenario_id);
    setInvestigation(null);
    setVerification(null);
    setReport(null);
    setReportSummary("");
    setPlans([]);
    setServiceFilter("all");
    setEvidenceQuery("");
    setError("");
    Promise.all([getScenarios(), getModelStatus()]).then(([items, status]) => {
      if (!active) return;
      setScenarios(items);
      setModel(status);
    }).catch((cause: unknown) => {
      if (active) setError(cause instanceof Error ? cause.message : "Could not load local integrations.");
    });
    void refreshDetails();
    return () => { active = false; };
  }, [incident.id, incident.scenario_id, refreshDetails]);

  useEffect(() => {
    const source = new EventSource("/api/events/stream");
    const handleEvent = (message: Event) => {
      const event = message as MessageEvent<string>;
      try {
        const item = JSON.parse(event.data) as ActivityEvent;
        if (item.incident_id === incident.id) {
          setEvents((current) => [item, ...current.filter((saved) => saved.id !== item.id)].slice(0, 40));
          onRefresh();
          void refreshDetails();
        }
      } catch {
        setError("Received an invalid lifecycle event from the local stream.");
      }
    };
    const eventTypes = Object.keys(eventLabels);
    for (const eventType of eventTypes) source.addEventListener(eventType, handleEvent);
    source.onopen = () => setStreamConnected(true);
    source.onerror = () => setStreamConnected(false);
    return () => {
      for (const eventType of eventTypes) source.removeEventListener(eventType, handleEvent);
      source.close();
    };
  }, [incident.id, onRefresh, refreshDetails]);

  const act = async (label: string, operation: () => Promise<unknown>) => {
    setBusy(label);
    setError("");
    try {
      await operation();
      await refreshDetails();
      onRefresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The requested operation failed.");
    } finally {
      setBusy("");
    }
  };

  const startInvestigation = () => act("investigate", async () => {
    const result = await investigate(incident.id);
    setInvestigation(result.investigation);
    setPlans(result.remediations);
  });

  const replayScenario = () => act("scenario", async () => {
    const state = await injectScenario(scenarioId);
    setScenarioId(state.scenario_id);
    setInvestigation(null);
    setVerification(null);
    setReport(null);
  });

  const approve = (plan: RemediationPlan) => act(`approve-${plan.id}`, async () => {
    const updated = await approveRemediation(plan.id, "local operator");
    setPlans((current) => current.map((item) => item.id === updated.id ? updated : item));
  });

  const execute = (plan: RemediationPlan) => act(`execute-${plan.id}`, async () => {
    await executeRemediation(plan.id);
  });

  const verify = () => act("verify", async () => {
    setVerification(await verifyIncident(incident.id));
  });

  const generateReport = () => act("report", async () => {
    setReport(await createReport(incident.id, reportSummary));
  });

  const evidenceById = useMemo(() => new Map(evidence.map((item) => [item.id, item])), [evidence]);
  const serviceIds = useMemo(() => [...new Set([...metrics.map((item) => item.service_id), ...evidence.map((item) => item.service_id)])].sort(), [metrics, evidence]);
  const visibleMetrics = metrics.filter((item) => serviceFilter === "all" || item.service_id === serviceFilter);
  const visibleEvidence = evidence.filter((item) => {
    const matchesService = serviceFilter === "all" || item.service_id === serviceFilter;
    const matchesQuery = !evidenceQuery.trim() || `${item.message} ${item.service_id} ${item.level}`.toLowerCase().includes(evidenceQuery.trim().toLowerCase());
    return matchesService && matchesQuery;
  });
  const safePlans = plans.filter((plan) => plan.status !== "blocked");
  const allRemediationsExecuted = safePlans.length > 0 && safePlans.every((plan) => plan.status === "executed");

  return (
    <div className="incident-workspace">
      <section className="panel workflow-control-panel" aria-busy={Boolean(busy)}>
        <header className="panel-heading">
          <div><span className="eyebrow">INCIDENT LIFECYCLE</span><h2>Investigate & respond</h2></div>
          <span className={`stream-chip ${streamConnected ? "connected" : ""}`}><i /> {streamConnected ? "LIVE EVENTS" : "RECONNECTING"}</span>
        </header>
        <div className="scenario-controls">
          <label><span>REPLAY SCENARIO</span><select value={scenarioId} onChange={(event) => setScenarioId(event.target.value)}>{scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.severity} · {scenario.title}</option>)}</select></label>
          <button className="secondary-button" type="button" disabled={Boolean(busy)} onClick={replayScenario}><RefreshCw size={13} /> {busy === "scenario" ? "Replaying…" : "Inject / reset"}</button>
        </div>
        <div className="model-status-row"><span className={`model-status-dot ${model?.available ? "online" : "offline"}`} /><span><b>Ollama</b><small>{model ? model.available ? `${model.model} · ${model.models.includes(model.model) ? "model available" : "service connected"}` : "Not connected · rules-based evidence fallback available" : "Checking local model…"}</small></span><span className={`model-state ${model?.available ? "online" : "offline"}`}>{model?.available ? "LOCAL" : "OFFLINE"}</span></div>
        <button className="primary-button full-button" type="button" disabled={Boolean(busy) || incident.status === "Resolved"} onClick={startInvestigation}><Sparkles size={14} /> {busy === "investigate" ? "Collecting evidence…" : investigation ? "Refresh investigation" : "Investigate incident"}</button>
        {busy && <p className="action-progress" role="status" aria-live="polite">Working on {busy === "scenario" ? "scenario replay" : busy === "verify" ? "recovery checks" : busy === "report" ? "incident report" : busy.startsWith("approve-") ? "approval" : busy.startsWith("execute-") ? "simulated remediation" : "investigation"}…</p>}
        {error && <div className="workspace-error" role="alert"><CircleAlert size={14} />{error}</div>}
      </section>

      <section className="panel workflow-progress-panel" aria-label="Incident response workflow">
        <header className="panel-heading"><div><span className="eyebrow">YOUR NEXT STEPS</span><h2>Response workflow</h2></div><span className="panel-count">{verification?.resolved ? "COMPLETE" : "IN PROGRESS"}</span></header>
        <ol className="workflow-stepper">
          <li className="complete"><span>1</span><div><strong>Signals detected</strong><small>Review the evidence below</small></div></li>
          <li className={investigation ? "complete" : "current"}><span>{investigation ? <Check size={12} /> : "2"}</span><div><strong>Investigate</strong><small>{investigation ? "Findings are ready" : "Collect and assess evidence"}</small></div></li>
          <li className={allRemediationsExecuted ? "complete" : plans.length ? "current" : "upcoming"}><span>{allRemediationsExecuted ? <Check size={12} /> : "3"}</span><div><strong>Apply safe fixes</strong><small>{plans.length ? `${safePlans.filter((plan) => plan.status === "executed").length} of ${safePlans.length} actions complete` : "Actions appear after investigation"}</small></div></li>
          <li className={verification?.resolved ? "complete" : allRemediationsExecuted ? "current" : "upcoming"}><span>{verification?.resolved ? <Check size={12} /> : "4"}</span><div><strong>Verify recovery</strong><small>{verification?.resolved ? "Recovery confirmed" : "Metrics must return to healthy"}</small></div></li>
        </ol>
      </section>

      <section className="panel telemetry-panel">
        <header className="panel-heading"><div><span className="eyebrow">OBSERVED SIGNALS</span><h2>Metrics & evidence</h2></div><span className="panel-count">{visibleMetrics.length} METRICS · {visibleEvidence.length} LOGS</span></header>
        <div className="evidence-toolbar">
          <label className="evidence-search"><Search size={13} /><input type="search" value={evidenceQuery} onChange={(event) => setEvidenceQuery(event.target.value)} placeholder="Search evidence…" aria-label="Search evidence" /></label>
          <label className="service-filter"><span className="sr-only">Filter telemetry by service</span><select value={serviceFilter} onChange={(event) => setServiceFilter(event.target.value)}><option value="all">All services</option>{serviceIds.map((id) => <option value={id} key={id}>{id}</option>)}</select></label>
        </div>
        <div className="telemetry-list">
          {visibleMetrics.map((metric, index) => {
            const breach = metric.operator === "gt" ? metric.value > metric.threshold : metric.operator === "gte" ? metric.value >= metric.threshold : metric.operator === "lt" ? metric.value < metric.threshold : metric.value <= metric.threshold;
            return <div className="telemetry-metric" key={`${metric.service_id}-${metric.name}-${index}`}><span className={`status-dot ${breach ? "critical" : "healthy"}`} /><span className="telemetry-name">{metric.service_id} · {metric.name}</span><strong className={breach ? "metric-breach" : ""}>{metric.value}{metric.unit}</strong><small>limit {metric.operator} {metric.threshold}{metric.unit}</small></div>;
          })}
          {!visibleMetrics.length && <p className="workspace-empty">No matching telemetry for this filter.</p>}
        </div>
        <div className="evidence-list">
          {visibleEvidence.map((item) => <article className="evidence-item" key={item.id}><span className={`evidence-level ${item.level}`}>{item.level}</span><div><div className="evidence-meta">{item.service_id} <time>{formatTime(item.observed_at)}</time></div><p>{item.message}</p></div></article>)}
          {!visibleEvidence.length && <p className="workspace-empty">No matching evidence. Adjust the search or service filter.</p>}
        </div>
      </section>

      {investigation && <section className="panel investigation-panel">
        <header className="panel-heading"><div><span className="eyebrow">{investigation.provider === "ollama" ? "LOCAL MODEL" : "EVIDENCE RULES"}</span><h2>Investigation findings</h2></div><span className="confidence-tag">UNCONFIRMED HYPOTHESES</span></header>
        <p className="investigation-summary">{investigation.summary}</p>
        <div className="fact-list">{investigation.facts.map((fact, index) => <p key={index}><Check size={12} />{fact}</p>)}</div>
        <div className="hypothesis-list">{investigation.hypotheses.map((hypothesis) => <article className="hypothesis-card" key={hypothesis.id}><div className="hypothesis-head"><strong>{hypothesis.statement}</strong><span>{Math.round(hypothesis.confidence * 100)}% confidence</span></div><p>{hypothesis.caveat}</p><div className="evidence-ref-list">Evidence: {hypothesis.evidence_ids.map((id) => <span key={id} title={evidenceById.get(id)?.message || "Evidence reference"}>{evidenceById.get(id)?.service_id || id}</span>)}</div></article>)}</div>
      </section>}

      {plans.length > 0 && <section className="panel remediation-panel">
        <header className="panel-heading"><div><span className="eyebrow">ALLOWLISTED SIMULATOR ACTIONS</span><h2>Remediation approvals</h2></div><ShieldCheck size={17} className="heading-icon" /></header>
        <div className="remediation-list">{plans.map((plan) => <article className={`remediation-card risk-${plan.risk} ${plan.status === "blocked" ? "is-blocked" : ""}`} key={plan.id}>
          <div className="remediation-icon">{plan.status === "executed" ? <Check size={15} /> : plan.status === "blocked" ? <AlertTriangle size={15} /> : <FlaskConical size={15} />}</div>
          <div className="remediation-copy"><div className="remediation-title"><strong>{plan.title}</strong><span className={`risk-pill ${plan.risk}`}>{plan.risk} risk</span></div><p>{plan.description}</p><small>{plan.reason} · Expected: {plan.expected_outcome}</small>{plan.approved_by && <small className="approval-note">Approved by {plan.approved_by} at {formatTime(plan.approval_at || plan.created_at)}</small>}</div>
          <div className="remediation-actions">{plan.status === "pending_approval" && <button className="approve-button" type="button" disabled={Boolean(busy)} onClick={() => approve(plan)}>Approve</button>}{plan.status === "approved" && <button className="execute-button" type="button" disabled={Boolean(busy)} onClick={() => execute(plan)}>{busy === `execute-${plan.id}` ? "Running…" : "Execute"}</button>}<span className={`plan-state ${plan.status}`}>{plan.status.replace("_", " ")}</span></div>
        </article>)}</div>
      </section>}

      <section className="panel verification-panel">
        <header className="panel-heading"><div><span className="eyebrow">RECOVERY GATES</span><h2>Verify incident recovery</h2></div><button className="secondary-button" type="button" disabled={Boolean(busy)} onClick={verify}><Activity size={13} /> Verify now</button></header>
        <p className="panel-helper">Resolution requires all scenario fixes, recovered metric thresholds, and healthy service status—not just a successful action response.</p>
        {verification && <div className={`verification-result ${verification.resolved ? "passed" : "pending"}`}><strong>{verification.resolved ? "Recovery verified" : "Not resolved yet"}</strong>{verification.checks.map((check) => <p key={check.name}><span className={check.passed ? "check-pass" : "check-fail"}>{check.passed ? "PASS" : "WAIT"}</span>{check.detail}</p>)}</div>}
        <div className="report-controls"><input aria-label="Incident report summary" value={reportSummary} onChange={(event) => setReportSummary(event.target.value)} placeholder="Optional incident report summary…" /><button className="secondary-button" type="button" disabled={Boolean(busy)} onClick={generateReport}><FileText size={13} /> Generate report</button></div>
        {report && <article className="report-card"><h3>{report.title}</h3><p>{report.summary}</p><small>{report.findings.length} findings · {report.evidence_ids.length} evidence records · {report.actions.length} simulated actions · {report.verification?.resolved ? "recovery verified" : "verification pending"}</small></article>}
      </section>

      <section className="panel activity-panel"><header className="panel-heading"><div><span className="eyebrow">AUDIT TIMELINE</span><h2>Agent activity & events</h2></div><span className="panel-count">{events.length} EVENTS</span></header><div className="event-list">{events.slice(0, 12).map((event) => <div className="event-row" key={event.id}><i /><span>{eventLabels[event.event_type] || event.event_type}</span><time>{formatTime(event.occurred_at)}</time></div>)}{!events.length && <p className="workspace-empty">Lifecycle events appear here in real time.</p>}</div></section>
    </div>
  );
}
