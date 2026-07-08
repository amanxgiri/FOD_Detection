import { MonitorPlay, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { STREAM_URL } from "../services/api";

interface LiveCameraProps {
  backendOnline: boolean;
  cameraStatus: string | undefined;
}

export function LiveCamera({ backendOnline, cameraStatus }: LiveCameraProps) {
  const [streamFailed, setStreamFailed] = useState(false);
  const cameraStreaming =
    cameraStatus === "online" || cameraStatus === "opening" || cameraStatus === "degraded";
  const streamSrc = `${STREAM_URL}?camera=${cameraStatus ?? "unknown"}&t=${
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
    <section className="video-surface" aria-label="Live camera feed">
      {showStream ? (
        <>
          <img
            className="video-frame"
            src={streamSrc}
            alt="Live annotated FOD camera stream"
            onError={() => setStreamFailed(true)}
          />
          <div className="video-badge">
            <MonitorPlay size={16} /> Stream connected
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
