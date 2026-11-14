import { useCallback, useEffect, useState } from "react";
import { getServices, getState } from "../services/api";
import type { Service, SimulatorState } from "../types/api";

export interface DashboardData {
  incidentState: SimulatorState | null;
  services: Service[];
  loading: boolean;
  error: string;
  refresh: () => void;
}

export function useDashboardData(): DashboardData {
  const [incidentState, setIncidentState] = useState<SimulatorState | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const refresh = useCallback(() => setReloadKey((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setLoading(true);

    Promise.all([getState(), getServices()])
      .then(([nextState, nextServices]) => {
        if (!active) return;
        setIncidentState(nextState);
        setServices(nextServices);
        setError("");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        setError(cause instanceof Error ? cause.message : "Could not connect to the local API.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [reloadKey]);

  return { incidentState, services, loading, error, refresh };
}
