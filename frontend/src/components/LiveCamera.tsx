import { MonitorPlay, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { cameraStreamUrl } from "../services/api";

interface LiveCameraProps {
  backendOnline: boolean;
  cameraId: string;
  displayName: string;
  modelId: string | null;
  cameraStatus: string | undefined;
}

export function LiveCamera({
  backendOnline,
  cameraId,
  displayName,
  modelId,
  cameraStatus
}: LiveCameraProps) {
  const [streamFailed, setStreamFailed] = useState(false);
  const cameraStreaming =
    cameraStatus === "online" || cameraStatus === "opening" || cameraStatus === "degraded";
  const streamSrc = `${cameraStreamUrl(cameraId)}?camera=${cameraStatus ?? "unknown"}&t=${
    backendOnline ? "online" : "offline"
  }`;
  const showStream = backendOnline && cameraStreaming && !streamFailed;
  const placeholderMessage = backendOnline
    ? cameraStatus === "stopped"
      ? "Camera stopped"
      : "Backend stream unavailable"
    : "Backend stream unavailable";
  const placeholderHint =
    backendOnline && cameraStatus === "stopped"
      ? "Use Start Camera to resume"
      : "Retrying automatically";

  useEffect(() => {
    setStreamFailed(false);
  }, [backendOnline, cameraStatus]);

  return (
    <section className="video-surface" aria-label={`${displayName} live camera feed`}>
      {showStream ? (
        <>
          <img
            className="video-frame"
            src={streamSrc}
            alt={`${displayName} live annotated FOD stream`}
            onError={() => setStreamFailed(true)}
          />
          <div className="video-badge">
            <MonitorPlay size={16} /> {displayName} · {modelId ?? "Preview only"}
          </div>
          <div
            className="latency-badge"
            title="Measured from laptop decode time to MJPEG send time; Pi encode, RTSP transit, and browser rendering are not included."
          >
            Latency overlay: laptop decode → stream
          </div>
        </>
      ) : (
        <div className="video-placeholder">
          <WifiOff size={40} />
          <p>{placeholderMessage}</p>
          <span>
            <RefreshCw size={14} /> {placeholderHint}
          </span>
        </div>
      )}
    </section>
  );
}
