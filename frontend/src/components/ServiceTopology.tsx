import { ArrowUpRight, Circle } from "lucide-react";
import type { Service } from "../types/api";

interface ServiceTopologyProps {
  services: Service[];
}

export function ServiceTopology({ services }: ServiceTopologyProps) {
  const groups = [...new Set(services.map((service) => service.group))];

  return (
    <section className="panel service-panel" aria-labelledby="service-heading">
      <header className="panel-heading">
        <div><span className="eyebrow">SYSTEM MAP</span><h2 id="service-heading">Service topology</h2></div>
        <span className="panel-count"><Circle size={8} /> {services.length} SERVICES</span>
      </header>
      <div className="service-groups">
        {groups.map((group) => {
          const members = services.filter((service) => service.group === group);
          return (
            <section className="service-group" key={group} aria-label={`${group} services`}>
              <div className="group-heading"><span>{group}</span><span>{String(members.length).padStart(2, "0")}</span></div>
              <div className="service-list">
                {members.map((service) => (
                  <article className="service-row" key={service.id} title={`Depends on: ${service.depends_on.join(", ") || "none"}`}>
                    <span className={`status-dot ${service.status}`} />
                    <span className="service-row-name">{service.name}</span>
                    <span className={`service-status ${service.status}`}>{service.status}</span>
                  </article>
                ))}
              </div>
            </section>
          );
        })}
      </div>
      <footer className="panel-footnote"><ArrowUpRight size={13} /> Service dependency metadata is loaded from the local simulator API.</footer>
    </section>
  );
}
