import type { SystemStatusState } from "../types/system";

interface SystemStatusProps {
  status: SystemStatusState;
}

export function SystemStatus({ status }: SystemStatusProps) {
  const data = status.data;

  return (
    <section className="panel">
      <h2>System Status</h2>
      {status.error ? <p className="panel-warning">{status.error}</p> : null}
      <dl>
        <div>
          <dt>API</dt>
          <dd>{status.error ? "Offline" : data?.backend_status ?? "Checking"}</dd>
        </div>
        <div>
          <dt>Camera</dt>
          <dd>{formatStatus(data?.camera_status)}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{formatStatus(data?.model_status)}</dd>
        </div>
        <div>
          <dt>Inference worker</dt>
          <dd>{formatStatus(data?.inference_status)}</dd>
        </div>
        <div>
          <dt>WebSocket</dt>
          <dd>{formatStatus(data?.websocket_status)}</dd>
        </div>
      </dl>
    </section>
  );
}

function formatStatus(value: string | undefined) {
  if (!value) {
    return "Unavailable";
  }
  return value.replaceAll("_", " ");
}
