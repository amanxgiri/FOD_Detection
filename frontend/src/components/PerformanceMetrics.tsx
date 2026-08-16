import type { SystemStatusResponse } from "../types/system";

interface PerformanceMetricsProps {
  status: SystemStatusResponse | null;
}

const CAMERA_IDS = ["camera_1", "camera_2", "camera_3"] as const;

export function PerformanceMetrics({ status }: PerformanceMetricsProps) {
  return (
    <section className="panel performance-panel">
      <h2>Performance</h2>

      <div className="camera-latency-list">
        {CAMERA_IDS.map((cameraId) => (
          <article className="camera-latency-card" key={cameraId}>
            <header>
              <span className="camera-status-dot" aria-hidden="true" />
              <h3>{formatCameraName(cameraId)}</h3>
            </header>
            <dl className="latency-metrics">
              <LatencyMetric
                label="Sensor to host"
                value={status?.capture_to_host_ms_by_camera?.[cameraId]}
              />
              <LatencyMetric
                label="Model inference"
                value={status?.inference_ms_by_camera?.[cameraId]}
              />
              <LatencyMetric
                emphasized
                label="Total latency"
                value={status?.total_latency_ms_by_camera?.[cameraId]}
              />
            </dl>
          </article>
        ))}
      </div>

      <h3 className="performance-summary-title">System throughput</h3>
      <dl className="performance-summary">
        <div>
          <dt>Capture FPS</dt>
          <dd>{formatMetric(status?.capture_fps)}</dd>
        </div>
        <div>
          <dt>Inference FPS</dt>
          <dd>{formatMetric(status?.inference_fps)}</dd>
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

interface LatencyMetricProps {
  emphasized?: boolean;
  label: string;
  value: number | null | undefined;
}

function LatencyMetric({ emphasized = false, label, value }: LatencyMetricProps) {
  const unavailable = value === null || value === undefined;
  return (
    <div className={emphasized ? "latency-total" : undefined}>
      <dt>{label}</dt>
      <dd className={unavailable ? "metric-unavailable" : undefined}>
        {formatNullableMetric(value, "ms")}
      </dd>
    </div>
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
  return `${value.toFixed(1)}${suffix ? ` ${suffix}` : ""}`;
}

function formatCameraName(cameraId: string) {
  return cameraId.replace("_", " ").replace(/^./, (value) => value.toUpperCase());
}
