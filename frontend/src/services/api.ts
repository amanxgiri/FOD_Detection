import type { SystemStatusResponse } from "../types/system";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const STREAM_URL = `${API_BASE_URL}/stream`;

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchSystemStatus(): Promise<SystemStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/system/status`);
  if (!response.ok) {
    throw new Error(`System status request failed: ${response.status}`);
  }
  return response.json() as Promise<SystemStatusResponse>;
}
