import { useCallback, useEffect, useState } from "react";

import { fetchCameras, fetchModels } from "../services/api";
import type { CameraRegistryState } from "../types/camera";

const POLL_INTERVAL_MS = 2000;

export function useCameras(): CameraRegistryState {
  const [state, setState] = useState<Omit<CameraRegistryState, "refresh">>({
    cameras: [],
    models: [],
    loading: true,
    error: null,
    warning: null,
    discoveryStatus: "checking"
  });

  const refresh = useCallback(async () => {
    try {
      const [cameras, models] = await Promise.all([fetchCameras(), fetchModels()]);
      setState({
        cameras: cameras.items,
        models: models.items,
        loading: false,
        error: null,
        warning: cameras.warning,
        discoveryStatus: cameras.discovery_status
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "Camera registry unavailable"
      }));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { ...state, refresh };
}
