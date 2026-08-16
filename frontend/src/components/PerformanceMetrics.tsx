import type { SystemStatusResponse } from "../types/system";
import type { CameraRecord } from "../types/camera";

interface PerformanceMetricsProps {
  status: SystemStatusResponse | null;
  cameras: CameraRecord[];
}

export function PerformanceMetrics({ status, cameras }: PerformanceMetricsProps) {
  return (
    <section className="panel performance-panel">
      <h2>Performance</h2>

      <div className="camera-latency-table" role="table" aria-label="Camera latency">
        <div className="camera-latency-table-header" role="row">
          <span role="columnheader">Camera</span>
          <span role="columnheader">Sensor to host</span>
          <span role="columnheader">Model inference</span>
          <span role="columnheader">Total latency</span>
        </div>
        {cameras.map((camera) => (
          <div className="camera-latency-table-row" role="row" key={camera.id}>
            <strong role="rowheader">
              <span className="camera-status-dot" aria-hidden="true" />
              {camera.display_name}
            </strong>
            <LatencyValue
              value={status?.capture_to_host_ms_by_camera?.[camera.id]}
            />
            <LatencyValue value={status?.inference_ms_by_camera?.[camera.id]} />
            <LatencyValue
              emphasized
              value={status?.total_latency_ms_by_camera?.[camera.id]}
            />
          </div>
        ))}
        {cameras.length === 0 ? (
          <p className="camera-table-empty">Waiting for a camera publisher…</p>
        ) : null}
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

interface LatencyValueProps {
  emphasized?: boolean;
  value: number | null | undefined;
}

function LatencyValue({ emphasized = false, value }: LatencyValueProps) {
  const unavailable = value === null || value === undefined;
  return (
    <span
      role="cell"
      className={`${emphasized ? "latency-total" : ""} ${
        unavailable ? "metric-unavailable" : ""
      }`.trim()}
    >
      {formatNullableMetric(value, "ms")}
    </span>
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
