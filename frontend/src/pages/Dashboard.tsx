import { AlertTriangle, Camera, Cpu, Power, PowerOff } from "lucide-react";
import { useEffect, useState } from "react";

import { ActiveAlert } from "../components/ActiveAlert";
import { LiveCamera } from "../components/LiveCamera";
import { PerformanceMetrics } from "../components/PerformanceMetrics";
import { SystemStatus } from "../components/SystemStatus";
import { useDetectionSocket } from "../hooks/useDetectionSocket";
import { useCameras } from "../hooks/useCameras";
import { useSystemStatus } from "../hooks/useSystemStatus";
import {
  acknowledgeDetection,
  assignCameraModel,
  forgetCamera,
  renameCamera,
  startCamera,
  startInference,
  stopCamera,
  stopInference
} from "../services/api";

type RuntimeCommand = "camera" | "inference";

export function Dashboard() {
  const status = useSystemStatus();
  const registry = useCameras();
  const backendOnline = !status.error && !status.loading;
  const data = status.data;
  const detectionSocket = useDetectionSocket(backendOnline);
  const [acknowledging, setAcknowledging] = useState(false);
  const [acknowledgeError, setAcknowledgeError] = useState<string | null>(null);
  const [commandPending, setCommandPending] = useState<RuntimeCommand | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [pendingCameraId, setPendingCameraId] = useState<string | null>(null);

  const cameraStatus = data?.camera_status;
  const cameraActive =
    cameraStatus === "online" || cameraStatus === "opening" || cameraStatus === "degraded";
  const inferenceStatus = data?.inference_status;
  const inferenceRunning = inferenceStatus === "running" || inferenceStatus === "starting";

  useEffect(() => {
    if (detectionSocket.latestEvent?.type.startsWith("camera.")) {
      void registry.refresh();
      void status.refresh();
    }
  }, [detectionSocket.latestEvent?.timestamp]);

  async function updateCamera(cameraId: string, action: () => Promise<unknown>) {
    setPendingCameraId(cameraId);
    setCommandError(null);
    try {
      await action();
      await Promise.all([registry.refresh(), status.refresh()]);
    } catch (error) {
      setCommandError(error instanceof Error ? error.message : "Camera update failed");
      await registry.refresh();
    } finally {
      setPendingCameraId(null);
    }
  }

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
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Camera size={22} />
          </span>
          <h1>FOD Detection</h1>
        </div>
        <div className="topbar-actions">
          <div className="runtime-controls" aria-label="Runtime controls">
            <button
              className={`runtime-control ${cameraActive ? "runtime-control-stop" : ""}`}
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
              className={`runtime-control ${inferenceRunning ? "runtime-control-stop" : ""}`}
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
        <div className={`camera-grid ${registry.cameras.length > 4 ? "camera-grid-scrollable" : ""}`} aria-label="Discovered camera feeds">
          {registry.cameras.map((camera) => (
            <LiveCamera
              key={camera.id}
              backendOnline={backendOnline}
              cameraId={camera.id}
              displayName={camera.display_name}
              modelId={camera.selected_model_id}
              cameraStatus={data?.camera_statuses?.[camera.id] ?? camera.stream_status}
            />
          ))}
          {!registry.loading && registry.cameras.length === 0 ? (
            <div className="camera-workspace-empty"><Camera size={36} /><strong>No cameras discovered</strong><span>Start a Pi publisher using its hostname as the RTSP path.</span></div>
          ) : null}
        </div>
        <div className="side-panel">
          <ActiveAlert
            icon={<AlertTriangle size={18} />}
            alert={detectionSocket.latestAlert}
            websocketConnected={detectionSocket.connected}
            acknowledging={acknowledging}
            acknowledgeError={acknowledgeError}
            onAcknowledge={handleAcknowledge}
          />
          <SystemStatus status={status} cameras={registry.cameras} models={registry.models}
            discoveryStatus={registry.discoveryStatus} warning={registry.warning ?? registry.error}
            pendingCameraId={pendingCameraId}
            onModelChange={(cameraId, modelId) => updateCamera(cameraId, () => assignCameraModel(cameraId, modelId))}
            onRename={(cameraId, name) => updateCamera(cameraId, () => renameCamera(cameraId, name))}
            onRemove={(cameraId) => updateCamera(cameraId, () => forgetCamera(cameraId))} />
          <PerformanceMetrics status={data} cameras={registry.cameras} />
        </div>
      </section>
    </main>
  );
}
