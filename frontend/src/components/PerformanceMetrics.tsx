import type { SystemStatusResponse } from "../types/system";

interface PerformanceMetricsProps {
  status: SystemStatusResponse | null;
}

export function PerformanceMetrics({ status }: PerformanceMetricsProps) {
  return (
    <section className="panel">
      <h2>Performance</h2>
      <dl>
        {(["camera_1", "camera_2", "camera_3"] as const).map((cameraId) => (
          <div className="camera-latency-group" key={cameraId}>
            <dt>{formatCameraName(cameraId)} latency</dt>
            <dd>
              Camera → host: {formatNullableMetric(
                status?.capture_to_host_ms_by_camera?.[cameraId],
                "ms"
              )}
              <br />
              Model inference: {formatNullableMetric(
                status?.inference_ms_by_camera?.[cameraId],
                "ms"
              )}
              <br />
              Total: {formatNullableMetric(
                status?.total_latency_ms_by_camera?.[cameraId],
                "ms"
              )}
            </dd>
          </div>
        ))}
        <div>
          <dt>Capture FPS</dt>
          <dd>{formatMetric(status?.capture_fps)}</dd>
        </div>
        <div>
          <dt>Inference FPS</dt>
          <dd>{formatMetric(status?.inference_fps)}</dd>
        </div>
        <div>
          <dt>Avg latency</dt>
          <dd>{formatMetric(status?.average_inference_ms, "ms")}</dd>
        </div>
        <div>
          <dt>Capture → host</dt>
          <dd>{formatNullableMetric(status?.capture_to_host_ms, "ms")}</dd>
        </div>
        <div>
          <dt>Avg capture → host</dt>
          <dd>{formatNullableMetric(status?.average_capture_to_host_ms, "ms")}</dd>
        </div>
        <div>
          <dt>Latest frame age</dt>
          <dd>{formatNullableMetric(status?.latest_frame_age_ms, "ms")}</dd>
        </div>
        <div>
          <dt>Confirmed count</dt>
          <dd>{status?.total_confirmed_detections ?? "Unavailable"}</dd>
        </div>
        <div>
          <dt>Active slot</dt>
          <dd>{status?.active_camera_id?.replace("_", " ") ?? "Idle"}</dd>
        </div>
        <div>
          <dt>Missed slots</dt>
          <dd>{status?.scheduler_missed_slots ?? "Unavailable"}</dd>
        </div>
      </dl>
    </section>
  );
}

function formatMetric(value: number | undefined, suffix = "") {
  if (value === undefined) {
    return "Unavailable";
  }
  return `${value.toFixed(1)}${suffix ? ` ${suffix}` : ""}`;
}

function formatNullableMetric(value: number | null | undefined, suffix = "") {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return `${value}${suffix ? ` ${suffix}` : ""}`;
}

function formatCameraName(cameraId: string) {
  return cameraId.replace("_", " ").replace(/^./, (value) => value.toUpperCase());
}
