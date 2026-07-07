import type { ReactNode } from "react";

import type { FodDetectedEvent } from "../types/alert";

interface ActiveAlertProps {
  icon: ReactNode;
  alert: FodDetectedEvent | null;
  websocketConnected: boolean;
  acknowledging: boolean;
  acknowledgeError: string | null;
  onAcknowledge: (detectionId: string) => void;
}

export function ActiveAlert({
  icon,
  alert,
  websocketConnected,
  acknowledging,
  acknowledgeError,
  onAcknowledge
}: ActiveAlertProps) {
  return (
    <section className="panel">
      <h2>{icon} Active Alert</h2>
      <p className={websocketConnected ? "connection-ok" : "panel-warning"}>
        WebSocket {websocketConnected ? "connected" : "reconnecting"}
      </p>
      {alert ? (
        <div className="alert-detail">
          <img src={alert.data.evidence_url} alt={`${alert.data.class_name} evidence`} />
          {acknowledgeError ? <p className="panel-warning">{acknowledgeError}</p> : null}
          <dl>
            <div>
              <dt>Type</dt>
              <dd>{alert.data.class_name}</dd>
            </div>
            <div>
              <dt>Confidence</dt>
              <dd>{Math.round(alert.data.confidence * 100)}%</dd>
            </div>
            <div>
              <dt>Time</dt>
              <dd>{new Date(alert.timestamp).toLocaleTimeString()}</dd>
            </div>
          </dl>
          <button
            className="primary-action"
            type="button"
            disabled={acknowledging}
            onClick={() => onAcknowledge(alert.data.detection_id)}
          >
            {acknowledging ? "Acknowledging..." : "Acknowledge"}
          </button>
        </div>
      ) : (
        <p>No confirmed FOD alert is active.</p>
      )}
    </section>
  );
}
