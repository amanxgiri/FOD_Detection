import type { SystemStatusResponse } from "../types/system";
import type { DetectionSummary } from "../types/detection";

const backendOrigin =
  import.meta.env.VITE_API_ORIGIN ??
  `${window.location.protocol}//${window.location.hostname || "localhost"}:8000`;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${backendOrigin}/api/v1`;
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

export async function acknowledgeDetection(detectionId: string): Promise<DetectionSummary> {
  const response = await fetch(`${API_BASE_URL}/detections/${detectionId}/acknowledge`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Acknowledge request failed: ${response.status}`);
  }
  const body = await response.json();
  return {
    id: body.id,
    className: body.class_name,
    confidence: body.confidence,
    status: body.status
  } as DetectionSummary;
}
