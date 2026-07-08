import { Activity, AlertTriangle, Camera, Cpu, Gauge, Power, PowerOff } from "lucide-react";
import { useState } from "react";

import { ActiveAlert } from "../components/ActiveAlert";
import { LiveCamera } from "../components/LiveCamera";
import { PerformanceMetrics } from "../components/PerformanceMetrics";
import { SystemStatus } from "../components/SystemStatus";
import { useDetectionSocket } from "../hooks/useDetectionSocket";
import { useSystemStatus } from "../hooks/useSystemStatus";
import {
  acknowledgeDetection,
  startCamera,
  startInference,
  stopCamera,
  stopInference
} from "../services/api";

type RuntimeCommand = "camera" | "inference";

export function Dashboard() {
  const status = useSystemStatus();
  const backendOnline = !status.error && !status.loading;
  const data = status.data;
  const detectionSocket = useDetectionSocket(backendOnline);
  const [acknowledging, setAcknowledging] = useState(false);
  const [acknowledgeError, setAcknowledgeError] = useState<string | null>(null);
  const [commandPending, setCommandPending] = useState<RuntimeCommand | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);

  const cameraStatus = data?.camera_status;
  const cameraActive =
    cameraStatus === "online" || cameraStatus === "opening" || cameraStatus === "degraded";
  const inferenceStatus = data?.inference_status;
  const inferenceRunning = inferenceStatus === "running" || inferenceStatus === "starting";

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

  async function handleRuntimeCommand(
    command: RuntimeCommand,
    action: () => Promise<unknown>
  ) {
    setCommandPending(command);
    setCommandError(null);
    try {
      await action();
      await status.refresh();
    } catch (error) {
      setCommandError(error instanceof Error ? error.message : "Runtime command failed");
      await status.refresh();
    } finally {
      setCommandPending(null);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar" aria-label="Dashboard summary">
        <div>
          <p className="eyebrow">Single-camera prototype</p>
          <h1>FOD Detection</h1>
        </div>
        <div className="topbar-actions">
          <div className="status-strip">
            <span>
              <Camera size={16} /> {cameraStatus?.replaceAll("_", " ") ?? "Camera pending"}
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
          <div className="runtime-controls" aria-label="Runtime controls">
            <button
              className="runtime-control"
              type="button"
              disabled={!backendOnline || commandPending !== null}
              onClick={() =>
                handleRuntimeCommand("camera", cameraActive ? stopCamera : startCamera)
              }
            >
              {cameraActive ? <PowerOff size={16} /> : <Power size={16} />}
              {commandPending === "camera"
                ? "Camera..."
                : cameraActive
                  ? "Stop Camera"
                  : "Start Camera"}
            </button>
            <button
              className="runtime-control"
              type="button"
              disabled={
                !backendOnline ||
                commandPending !== null ||
                (!inferenceRunning && cameraStatus !== "online")
              }
              onClick={() =>
                handleRuntimeCommand(
                  "inference",
                  inferenceRunning ? stopInference : startInference
                )
              }
            >
              <Cpu size={16} />
              {commandPending === "inference"
                ? "Inference..."
                : inferenceRunning
                  ? "Stop Inference"
                  : "Start Inference"}
            </button>
          </div>
          {commandError ? <p className="runtime-command-error">{commandError}</p> : null}
        </div>
      </section>

      <section className="dashboard-grid">
        <LiveCamera backendOnline={backendOnline} cameraStatus={cameraStatus} />
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
