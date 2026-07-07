import type { DetectionSummary } from "../types/detection";

interface DetectionCardProps {
  detection: DetectionSummary;
}

export function DetectionCard({ detection }: DetectionCardProps) {
  return (
    <article className="panel">
      <h2>{detection.className}</h2>
      <p>{Math.round(detection.confidence * 100)}% confidence</p>
    </article>
  );
}
