import type { SystemStatusState } from "../types/system";

interface SystemStatusProps {
  status: SystemStatusState;
}

export function SystemStatus({ status }: SystemStatusProps) {
  const data = status.data;
  const healthy =
    !status.error &&
    data?.backend_status === "online" &&
    data.inference_status === "running" &&
    data.websocket_status === "connected" &&
    data.camera_status === "online" &&
    data.model_status === "loaded";

  return (
    <section className="panel system-status-panel">
      <div className="panel-heading">
        <div>
          <h2>System status</h2>
          <p>Live service health</p>
        </div>
        <StatusBadge value={healthy ? "Operational" : "Attention"} />
      </div>
      {status.error ? <p className="panel-warning">{status.error}</p> : null}

      <div className="service-status-list">
        <StatusRow
          label="API service"
          value={status.error ? "Offline" : data?.backend_status ?? "Checking"}
        />
        <StatusRow label="Inference" value={data?.inference_status} />
        <StatusRow label="Realtime events" value={data?.websocket_status} />
      </div>

      <h3 className="status-section-title">Camera services</h3>
      <article className="camera-health-card">
        <strong>All cameras</strong>
        <div>
          <span>Stream</span>
          <StatusBadge value={data?.camera_status} />
        </div>
        <div>
          <span>Model</span>
          <StatusBadge value={data?.model_status} />
        </div>
      </article>
    </section>
  );
}

interface StatusRowProps {
  label: string;
  value: string | undefined;
}

function StatusRow({ label, value }: StatusRowProps) {
  return (
    <div className="service-status-row">
      <span>{label}</span>
      <StatusBadge value={value} />
    </div>
  );
}

function StatusBadge({ value }: { value: string | undefined }) {
  const normalized = value?.toLowerCase() ?? "unavailable";
  const tone = getStatusTone(normalized);
  return (
    <span className={`status-badge status-badge-${tone}`}>
      <span aria-hidden="true" />
      {formatStatus(normalized)}
    </span>
  );
}

function getStatusTone(value: string) {
  if (["online", "loaded", "running", "connected", "operational"].includes(value)) {
    return "healthy";
  }
  if (["opening", "starting", "degraded", "checking", "attention"].includes(value)) {
    return "warning";
  }
  return "neutral";
}

function formatStatus(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
