import { MonitorPlay, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";

import { STREAM_URL } from "../services/api";

interface LiveCameraProps {
  backendOnline: boolean;
}

export function LiveCamera({ backendOnline }: LiveCameraProps) {
  const [streamFailed, setStreamFailed] = useState(false);
  const streamSrc = `${STREAM_URL}?t=${backendOnline ? "online" : "offline"}`;
  const showStream = backendOnline && !streamFailed;

  useEffect(() => {
    setStreamFailed(false);
  }, [backendOnline]);

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
          <p>Backend stream unavailable</p>
          <span>
            <RefreshCw size={14} /> Retrying automatically
          </span>
        </div>
      )}
    </section>
  );
}
