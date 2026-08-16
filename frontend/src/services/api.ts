import type { SystemStatusResponse } from "../types/system";
import type { DetectionSummary } from "../types/detection";
import type {
  CameraListResponse,
  CameraRecord,
  ModelListResponse
} from "../types/camera";

const backendOrigin =
  import.meta.env.VITE_API_ORIGIN ??
  `${window.location.protocol}//${window.location.hostname || "localhost"}:8000`;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `${backendOrigin}/api/v1`;
export function cameraStreamUrl(cameraId: string) {
  return `${API_BASE_URL}/cameras/${cameraId}/stream`;
}

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

export async function fetchCameras(): Promise<CameraListResponse> {
  return getJson<CameraListResponse>("/cameras", "Camera list");
}

export async function fetchModels(): Promise<ModelListResponse> {
  return getJson<ModelListResponse>("/models", "Model catalog");
}

export async function addCamera(source: string): Promise<CameraRecord> {
  const response = await fetch(`${API_BASE_URL}/cameras`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source })
  });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return response.json() as Promise<CameraRecord>;
}

export async function renameCamera(
  cameraId: string,
  displayName: string | null
): Promise<CameraRecord> {
  return sendCameraRequest(cameraId, "PATCH", { display_name: displayName });
}

export async function assignCameraModel(
  cameraId: string,
  modelId: string | null
): Promise<CameraRecord> {
  return sendCameraRequest(cameraId, "PUT", { model_id: modelId }, "/model");
}

export async function forgetCamera(cameraId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/cameras/${encodeURIComponent(cameraId)}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error(await readErrorDetail(response));
}

export function startCamera(): Promise<SystemStatusResponse> {
  return postRuntimeCommand("/camera/start");
}

export function stopCamera(): Promise<SystemStatusResponse> {
  return postRuntimeCommand("/camera/stop");
}

export function startInference(): Promise<SystemStatusResponse> {
  return postRuntimeCommand("/inference/start");
}

export function stopInference(): Promise<SystemStatusResponse> {
  return postRuntimeCommand("/inference/stop");
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

async function postRuntimeCommand(path: string): Promise<SystemStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/runtime${path}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }
  return response.json() as Promise<SystemStatusResponse>;
}

async function getJson<T>(path: string, label: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) throw new Error(`${label} request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

async function sendCameraRequest(
  cameraId: string,
  method: "PATCH" | "PUT",
  body: object,
  suffix = ""
): Promise<CameraRecord> {
  const response = await fetch(
    `${API_BASE_URL}/cameras/${encodeURIComponent(cameraId)}${suffix}`,
    {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }
  );
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return response.json() as Promise<CameraRecord>;
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall through to a generic status-based message.
  }
  return `Runtime command failed: ${response.status}`;
}
