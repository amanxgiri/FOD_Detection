export interface SystemStatusResponse {
  camera_status: string;
  model_status: string;
  inference_status: string;
  backend_status: string;
  websocket_status: string;
  capture_fps: number;
  inference_fps: number;
  average_inference_ms: number;
  latest_frame_age_ms: number | null;
  total_confirmed_detections: number;
}

export interface SystemStatusState {
  data: SystemStatusResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  refresh: () => Promise<void>;
}
