import { useEffect, useState } from "react";

import { fetchSystemStatus } from "../services/api";
import type { SystemStatusState } from "../types/system";

const POLL_MS = 3000;

export function useSystemStatus(): SystemStatusState {
  const [state, setState] = useState<SystemStatusState>({
    data: null,
    loading: true,
    error: null,
    lastUpdatedAt: null
  });

  useEffect(() => {
    let cancelled = false;

    async function loadStatus() {
      try {
        const data = await fetchSystemStatus();
        if (!cancelled) {
          setState({
            data,
            loading: false,
            error: null,
            lastUpdatedAt: new Date()
          });
        }
      } catch (error) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            loading: false,
            error: error instanceof Error ? error.message : "Backend unavailable"
          }));
        }
      }
    }

    void loadStatus();
    const intervalId = window.setInterval(loadStatus, POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return state;
}
