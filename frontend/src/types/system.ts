export interface SystemStatusResponse {
  camera_status: string;
  camera_statuses: Record<string, string>;
  model_status: string;
  model_statuses: Record<string, string>;
  inference_status: string;
  active_camera_id: string | null;
  scheduler_slot_count: number;
  scheduler_missed_slots: number;
  backend_status: string;
  websocket_status: string;
  capture_fps: number;
  inference_fps: number;
  average_inference_ms: number;
  latest_frame_age_ms: number | null;
  capture_to_host_ms: number | null;
  average_capture_to_host_ms: number | null;
  source_timestamp_frames: number;
  total_confirmed_detections: number;
}

export interface SystemStatusState {
  data: SystemStatusResponse | null;
  loading: boolean;
  error: string | null;
  lastUpdatedAt: Date | null;
  refresh: () => Promise<void>;
}
