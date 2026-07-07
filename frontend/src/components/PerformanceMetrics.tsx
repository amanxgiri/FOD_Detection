import type { SystemStatusResponse } from "../types/system";

interface PerformanceMetricsProps {
  status: SystemStatusResponse | null;
}

export function PerformanceMetrics({ status }: PerformanceMetricsProps) {
  return (
    <section className="panel">
      <h2>Performance</h2>
      <dl>
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
          <dt>Latest frame age</dt>
          <dd>{formatNullableMetric(status?.latest_frame_age_ms, "ms")}</dd>
        </div>
        <div>
          <dt>Confirmed count</dt>
          <dd>{status?.total_confirmed_detections ?? "Unavailable"}</dd>
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
