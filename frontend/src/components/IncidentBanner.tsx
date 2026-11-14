import { AlertTriangle, Clock3, RadioTower } from "lucide-react";
import type { Incident } from "../types/api";

interface IncidentBannerProps {
  incident: Incident;
  elapsedMinutes: number;
  resolved: boolean;
}

function formatElapsed(minutes: number): string {
  return minutes >= 60
    ? `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    : `${minutes}m`;
}

export function IncidentBanner({ incident, elapsedMinutes, resolved }: IncidentBannerProps) {
  return (
    <section className={`incident-banner${resolved ? " is-resolved" : ""}`} aria-label="Active incident">
      <div className="incident-icon"><AlertTriangle size={19} /></div>
      <div className="incident-copy">
        <div className="incident-title-row">
          <span className={`severity-badge severity-${incident.severity.toLowerCase()}`}>{incident.severity}</span>
          <h2>{incident.title}</h2>
          <span className={`incident-status ${resolved ? "resolved" : "open"}`}>
            <i /> {resolved ? "MITIGATED" : incident.status.toUpperCase()}
          </span>
        </div>
        <p>{incident.impact}</p>
      </div>
      <div className="incident-meta">
        <span><Clock3 size={13} /> {formatElapsed(elapsedMinutes)}</span>
        <span><RadioTower size={13} /> {incident.trigger}</span>
      </div>
    </section>
  );
}
