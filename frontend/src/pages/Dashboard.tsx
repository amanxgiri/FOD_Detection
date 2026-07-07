import { Activity, AlertTriangle, Camera, Gauge } from "lucide-react";

import { ActiveAlert } from "../components/ActiveAlert";
import { LiveCamera } from "../components/LiveCamera";
import { PerformanceMetrics } from "../components/PerformanceMetrics";
import { SystemStatus } from "../components/SystemStatus";
import { useSystemStatus } from "../hooks/useSystemStatus";

export function Dashboard() {
  const status = useSystemStatus();
  const backendOnline = !status.error && !status.loading;
  const data = status.data;

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
        </div>
      </section>

      <section className="dashboard-grid">
        <LiveCamera backendOnline={backendOnline} />
        <div className="side-panel">
          <ActiveAlert icon={<AlertTriangle size={18} />} />
          <SystemStatus status={status} />
          <PerformanceMetrics status={data} />
        </div>
      </section>
    </main>
  );
}
