export interface CameraRecord {
  id: string;
  display_name: string;
  hostname: string;
  rtsp_path: string;
  publisher_ip: string | null;
  stream_status: string;
  selected_model_id: string | null;
  model_status: string;
  discovered_at: string;
  last_seen_at: string;
}

export interface CameraListResponse {
  items: CameraRecord[];
  max_cameras: number;
  discovery_status: string;
  warning: string | null;
}

export interface ModelRecord {
  id: string;
  display_name: string;
  status: string;
}

export interface ModelListResponse {
  items: ModelRecord[];
}

export interface CameraRegistryState {
  cameras: CameraRecord[];
  models: ModelRecord[];
  loading: boolean;
  error: string | null;
  warning: string | null;
  discoveryStatus: string;
  refresh: () => Promise<void>;
}
