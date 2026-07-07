import type { ReactNode } from "react";

import type { FodDetectedEvent } from "../types/alert";

interface ActiveAlertProps {
  icon: ReactNode;
  alert: FodDetectedEvent | null;
  websocketConnected: boolean;
}

export function ActiveAlert({ icon, alert, websocketConnected }: ActiveAlertProps) {
  return (
    <section className="panel">
      <h2>{icon} Active Alert</h2>
      <p className={websocketConnected ? "connection-ok" : "panel-warning"}>
        WebSocket {websocketConnected ? "connected" : "reconnecting"}
      </p>
      {alert ? (
        <div className="alert-detail">
          <img src={alert.data.evidence_url} alt={`${alert.data.class_name} evidence`} />
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
        </div>
      ) : (
        <p>No confirmed FOD alert is active.</p>
      )}
    </section>
  );
}
