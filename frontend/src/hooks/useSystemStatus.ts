import { useCallback, useEffect, useState } from "react";

import { fetchSystemStatus } from "../services/api";
import type { SystemStatusResponse, SystemStatusState } from "../types/system";

const POLL_MS = 3000;
type StatusState = Omit<SystemStatusState, "refresh">;

export function useSystemStatus(): SystemStatusState {
  const [state, setState] = useState<StatusState>({
    data: null,
    loading: true,
    error: null,
    lastUpdatedAt: null
  });

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const data: SystemStatusResponse = await fetchSystemStatus();
      setState({
        data,
        loading: false,
        error: null,
        lastUpdatedAt: new Date()
      });
    } catch (error) {
      setState((current) => ({
        ...current,
        loading: false,
        error: error instanceof Error ? error.message : "Backend unavailable"
      }));
    }
  }, []);

  useEffect(() => {
    void refresh();
    const intervalId = window.setInterval(refresh, POLL_MS);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [refresh]);

  return { ...state, refresh };
}
