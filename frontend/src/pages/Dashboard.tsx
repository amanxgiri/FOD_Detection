import { Activity, AlertTriangle, Camera, Gauge } from "lucide-react";

import { ActiveAlert } from "../components/ActiveAlert";
import { LiveCamera } from "../components/LiveCamera";
import { PerformanceMetrics } from "../components/PerformanceMetrics";
import { SystemStatus } from "../components/SystemStatus";

export function Dashboard() {
  return (
    <main className="app-shell">
      <section className="topbar" aria-label="Dashboard summary">
        <div>
          <p className="eyebrow">Single-camera prototype</p>
          <h1>FOD Detection</h1>
        </div>
        <div className="status-strip">
          <span>
            <Camera size={16} /> Camera not started
          </span>
          <span>
            <Activity size={16} /> Model not started
          </span>
          <span>
            <Gauge size={16} /> Metrics pending
          </span>
        </div>
      </section>

      <section className="dashboard-grid">
        <LiveCamera />
        <div className="side-panel">
          <ActiveAlert icon={<AlertTriangle size={18} />} />
          <SystemStatus />
          <PerformanceMetrics />
        </div>
      </section>
    </main>
  );
}
