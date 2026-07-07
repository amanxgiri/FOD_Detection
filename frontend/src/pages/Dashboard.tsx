import { Activity, AlertTriangle, Camera, Gauge } from "lucide-react";
import { useState } from "react";

import { ActiveAlert } from "../components/ActiveAlert";
import { LiveCamera } from "../components/LiveCamera";
import { PerformanceMetrics } from "../components/PerformanceMetrics";
import { SystemStatus } from "../components/SystemStatus";
import { useDetectionSocket } from "../hooks/useDetectionSocket";
import { useSystemStatus } from "../hooks/useSystemStatus";
import { acknowledgeDetection } from "../services/api";

export function Dashboard() {
  const status = useSystemStatus();
  const backendOnline = !status.error && !status.loading;
  const data = status.data;
  const detectionSocket = useDetectionSocket(backendOnline);
  const [acknowledging, setAcknowledging] = useState(false);
  const [acknowledgeError, setAcknowledgeError] = useState<string | null>(null);

  async function handleAcknowledge(detectionId: string) {
    setAcknowledging(true);
    setAcknowledgeError(null);
    try {
      await acknowledgeDetection(detectionId);
      detectionSocket.clearLatestAlert(detectionId);
    } catch (error) {
      setAcknowledgeError(
        error instanceof Error ? error.message : "Acknowledge request failed"
      );
    } finally {
      setAcknowledging(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar" aria-label="Dashboard summary">
        <div>
          <p className="eyebrow">Single-camera prototype</p>
          <h1>FOD Detection</h1>
        </div>
        <div className="status-strip">
          <span>
            <Camera size={16} /> {data?.camera_status?.replaceAll("_", " ") ?? "Camera pending"}
          </span>
          <span>
            <Activity size={16} /> {data?.model_status?.replaceAll("_", " ") ?? "Model pending"}
          </span>
          <span>
            <Gauge size={16} /> {backendOnline ? "Metrics live" : "Metrics unavailable"}
          </span>
          <span>
            <AlertTriangle size={16} /> {detectionSocket.connected ? "Alerts live" : "Alerts pending"}
          </span>
        </div>
      </section>

      <section className="dashboard-grid">
        <LiveCamera backendOnline={backendOnline} />
        <div className="side-panel">
          <ActiveAlert
            icon={<AlertTriangle size={18} />}
            alert={detectionSocket.latestAlert}
            websocketConnected={detectionSocket.connected}
            acknowledging={acknowledging}
            acknowledgeError={acknowledgeError}
            onAcknowledge={handleAcknowledge}
          />
          <SystemStatus status={status} />
          <PerformanceMetrics status={data} />
        </div>
      </section>
    </main>
  );
}
