export interface DetectionSummary {
  id: string;
  className: string;
  confidence: number;
  status: "ACTIVE" | "ACKNOWLEDGED";
}
