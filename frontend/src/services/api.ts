import type { Service, SimulatorState } from "../types/api";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getState = () => getJson<SimulatorState>("/api/state");
export const getServices = () => getJson<Service[]>("/api/services");
