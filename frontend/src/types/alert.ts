export interface BoundingBoxEventData {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface FodDetectedData {
  detection_id: string;
  class_name: string;
  confidence: number;
  bbox: BoundingBoxEventData;
  evidence_url: string;
}

export type AlertEventType =
  | "fod.detected"
  | "fod.acknowledged"
  | "camera.offline"
  | "camera.online"
  | "system.warning";

export interface AlertEvent<TData = unknown> {
  type: AlertEventType;
  timestamp: string;
  data: TData;
}

export type FodDetectedEvent = AlertEvent<FodDetectedData>;
