import { Activity, Database, RefreshCw, Shield, Wifi } from "lucide-react";
import { IncidentWorkspace } from "../components/IncidentWorkspace";
import { IncidentBanner } from "../components/IncidentBanner";
import { ServiceTopology } from "../components/ServiceTopology";
import type { DashboardData } from "../hooks/useDashboardData";

interface DashboardPageProps extends DashboardData {}

export function DashboardPage({ incidentState, services, loading, error, refresh }: DashboardPageProps) {
  const affected = services.filter((service) => service.status !== "healthy").length;
  const critical = services.filter((service) => service.status === "critical").length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Nightwatch AI home">
          <span className="brand-mark"><Activity size={19} /></span>
          <span>nightwatch<span className="brand-light">.ai</span></span>
          <span className="env-tag">LOCAL LAB</span>
        </a>
        <div className="topbar-right">
          <span className="connection-status"><i /> LOCAL SIMULATOR</span>
          <span className="top-divider" />
          <button className="icon-button" type="button" title="Refresh dashboard" aria-label="Refresh dashboard" onClick={refresh}>
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      <main id="top" className="dashboard-main">
        <section className="page-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-bar" /> ON-CALL COMMAND CENTER <span className="exercise-id">SIMULATION</span></div>
            <h1>Incident <span>overview</span></h1>
            <p className="page-subtitle">A local-first foundation for evidence-led incident response.</p>
          </div>
          <div className="model-chip"><span className="stack-dot" /><span><b>LOCAL STACK</b><small>Simulator · SQLite · Ollama</small></span></div>
        </section>

        {error ? (
          <section className="connection-error" role="alert">
            <div><Wifi size={18} /><div><strong>Could not connect to the Nightwatch API</strong><p>{error} Start the backend using the setup steps in the README.</p></div></div>
            <button type="button" onClick={refresh}>Retry</button>
          </section>
        ) : loading && !incidentState ? (
          <section className="loading-panel" aria-live="polite"><span className="loader" /> Connecting to local simulator…</section>
        ) : incidentState ? (
          <>
            <IncidentBanner incident={incidentState.incident} elapsedMinutes={incidentState.elapsed_minutes} resolved={incidentState.resolved} />

            <section className="stats-row" aria-label="Incident summary">
              <article className="stat-card"><span className="stat-label">AFFECTED SERVICES</span><strong>{affected}<small> / {services.length}</small></strong><span className="stat-foot">{critical} critical · {affected - critical} degraded</span></article>
              <article className="stat-card"><span className="stat-label">INCIDENT STATUS</span><strong className={incidentState.resolved ? "value-good" : "value-alert"}>{incidentState.resolved ? "Mitigated" : "Investigating"}</strong><span className="stat-foot">Scenario-backed state</span></article>
              <article className="stat-card"><span className="stat-label">MONITORED NODES</span><strong>{services.length}<small> services</small></strong><span className="stat-foot"><Database size={12} /> Seeded local topology</span></article>
              <article className="stat-card"><span className="stat-label">RESPONSE GUARDRAILS</span><strong className="value-good">Enabled</strong><span className="stat-foot"><Shield size={12} /> Simulation-only actions</span></article>
            </section>

            <div className="content-grid">
              <ServiceTopology services={services} />
              <div className="side-column">
                <IncidentWorkspace incident={incidentState.incident} onRefresh={refresh} />
              </div>
            </div>
            <footer className="page-footer"><span>NIGHTWATCH AI <b>·</b> LOCAL SIMULATION ONLY</span><span>Migration scaffold · no production systems connected</span></footer>
          </>
        ) : null}
      </main>
    </div>
  );
}
