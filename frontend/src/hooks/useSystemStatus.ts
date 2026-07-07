export function useSystemStatus() {
  return {
    cameraStatus: "not_started",
    modelStatus: "not_started",
    inferenceStatus: "not_started"
  };
}
