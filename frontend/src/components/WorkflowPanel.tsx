import { Activity, BrainCircuit, FileSearch, ShieldCheck } from "lucide-react";

const steps = [
  { icon: Activity, title: "Incident detection", detail: "Scenario detection is being connected", state: "in progress" },
  { icon: FileSearch, title: "Evidence collection", detail: "Metrics and logs will appear here", state: "queued" },
  { icon: BrainCircuit, title: "AI investigation", detail: "Local Ollama integration comes next", state: "queued" },
  { icon: ShieldCheck, title: "Safe response", detail: "Approval and recovery checks come next", state: "queued" },
];

export function WorkflowPanel() {
  return (
    <section className="panel workflow-panel" aria-labelledby="workflow-heading">
      <header className="panel-heading">
        <div><span className="eyebrow">INCIDENT LIFECYCLE</span><h2 id="workflow-heading">Investigation progress</h2></div>
        <span className="stage-pill">FOUNDATION</span>
      </header>
      <div className="workflow-list">
        {steps.map(({ icon: Icon, title, detail, state }, index) => (
          <div className={`workflow-step ${state.replace(" ", "-")}`} key={title}>
            <div className="step-icon"><Icon size={16} /></div>
            <div className="step-copy"><strong>{title}</strong><span>{detail}</span></div>
            <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
          </div>
        ))}
      </div>
      <p className="workflow-note">This is the migration scaffold. Recommendations and controls will remain unavailable until the simulator, evidence, and approval APIs are implemented.</p>
    </section>
  );
}
