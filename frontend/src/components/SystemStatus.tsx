import { Check, Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import type { CameraRecord, ModelRecord } from "../types/camera";
import type { SystemStatusState } from "../types/system";

interface SystemStatusProps {
  status: SystemStatusState;
  cameras: CameraRecord[];
  models: ModelRecord[];
  discoveryStatus: string;
  warning: string | null;
  pendingCameraId: string | null;
  onAdd: (source: string) => Promise<boolean>;
  onModelChange: (cameraId: string, modelId: string | null) => Promise<boolean>;
  onRename: (cameraId: string, name: string | null) => Promise<boolean>;
  onRemove: (cameraId: string) => Promise<boolean>;
}

export function SystemStatus({ status, cameras, models, discoveryStatus, warning,
  pendingCameraId, onAdd, onModelChange, onRename, onRemove }: SystemStatusProps) {
  const [cameraSource, setCameraSource] = useState("");
  const data = status.data;
  const healthy = !status.error && data?.backend_status === "online" &&
    data.websocket_status === "connected" && discoveryStatus === "online";

  return (
    <section className="panel system-status-panel">
      <div className="panel-heading">
        <div><h2>System status</h2><p>Services and discovered cameras</p></div>
        <StatusBadge value={healthy ? "Operational" : "Attention"} />
      </div>
      {status.error ? <p className="panel-warning">{status.error}</p> : null}
      {warning ? <p className="panel-warning compact-warning">{warning}</p> : null}
      <div className="service-status-list">
        <StatusRow label="API" value={status.error ? "Offline" : data?.backend_status} />
        <StatusRow label="Inference" value={data?.inference_status} />
        <StatusRow label="Discovery" value={discoveryStatus} />
      </div>
      <h3 className="status-section-title">Camera services</h3>
      <form className="camera-add-form" onSubmit={async (event) => {
        event.preventDefault();
        if (await onAdd(cameraSource.trim())) setCameraSource("");
      }}>
        <input type="text" required placeholder="0, /dev/video0, or rtsp://host/stream"
          aria-label="Camera source" value={cameraSource}
          onChange={(event) => setCameraSource(event.target.value)} />
        <button type="submit" disabled={!cameraSource.trim() || pendingCameraId === "new-camera"}>
          <Plus size={13} />{pendingCameraId === "new-camera" ? "Adding…" : "Add"}
        </button>
      </form>
      <div className={`camera-service-list ${cameras.length > 4 ? "scrollable" : ""}`}>
        {cameras.map((camera) => (
          <CameraServiceRow key={camera.id} camera={camera} models={models}
            pending={pendingCameraId === camera.id} onModelChange={onModelChange}
            onRename={onRename} onRemove={onRemove} />
        ))}
        {cameras.length === 0 ? <p className="camera-services-empty">Waiting for MediaMTX publishers…</p> : null}
      </div>
    </section>
  );
}

function CameraServiceRow({ camera, models, pending, onModelChange, onRename, onRemove }: {
  camera: CameraRecord;
  models: ModelRecord[];
  pending: boolean;
  onModelChange: (cameraId: string, modelId: string | null) => Promise<boolean>;
  onRename: (cameraId: string, name: string | null) => Promise<boolean>;
  onRemove: (cameraId: string) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(camera.display_name);
  async function saveName() {
    if (await onRename(camera.id, name.trim() || null)) setEditing(false);
  }
  return (
    <article className="camera-service-row">
      <div className="camera-service-identity">
        {editing ? (
          <div className="camera-name-editor">
            <input aria-label={`Rename ${camera.display_name}`} value={name} maxLength={128}
              onChange={(event) => setName(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && void saveName()} />
            <button type="button" aria-label="Save name" onClick={() => void saveName()}><Check size={13} /></button>
            <button type="button" aria-label="Cancel rename" onClick={() => setEditing(false)}><X size={13} /></button>
          </div>
        ) : (
          <div className="camera-service-name">
            <strong title={camera.hostname}>{camera.display_name}</strong>
            <button type="button" aria-label={`Rename ${camera.display_name}`} onClick={() => setEditing(true)}><Pencil size={12} /></button>
          </div>
        )}
        <StatusBadge value={camera.stream_status} />
      </div>
      <div className="camera-model-control">
        <select aria-label={`Model for ${camera.display_name}`} value={camera.selected_model_id ?? ""}
          disabled={pending} onChange={(event) => void onModelChange(camera.id, event.target.value || null)}>
          <option value="">Preview only</option>
          {models.map((model) => <option value={model.id} key={model.id}>{model.display_name}</option>)}
        </select>
        <span className={`model-state model-state-${camera.model_status}`}>
          {pending ? "Updating…" : formatStatus(camera.model_status)}
        </span>
      </div>
      <button className="camera-remove" type="button"
        title="Remove camera"
        aria-label={`Remove ${camera.display_name}`} disabled={pending}
        onClick={() => void onRemove(camera.id)}><Trash2 size={14} /></button>
      {camera.latency_message ? (
        <p className="camera-latency-warning">{camera.latency_message}</p>
      ) : null}
    </article>
  );
}

function StatusRow({ label, value }: { label: string; value?: string }) {
  return <div className="service-status-row"><span>{label}</span><StatusBadge value={value} /></div>;
}

function StatusBadge({ value }: { value?: string }) {
  const normalized = value?.toLowerCase() ?? "unavailable";
  return <span className={`status-badge status-badge-${getStatusTone(normalized)}`}>
    <span aria-hidden="true" />{formatStatus(normalized)}</span>;
}

function getStatusTone(value: string) {
  if (["online", "loaded", "running", "connected", "operational", "assigned"].includes(value)) return "healthy";
  if (["opening", "starting", "loading", "degraded", "attention"].includes(value)) return "warning";
  return "neutral";
}

function formatStatus(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
