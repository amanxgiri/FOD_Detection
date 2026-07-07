import { MonitorPlay } from "lucide-react";

export function LiveCamera() {
  return (
    <section className="video-surface" aria-label="Live camera feed">
      <div className="video-placeholder">
        <MonitorPlay size={40} />
        <p>Live stream connects in Milestone 5</p>
      </div>
    </section>
  );
}
