import { useEffect, useRef, useState } from "react";

import { EVENTS_WS_URL } from "../services/websocket";
import type { AlertEvent, FodDetectedData, FodDetectedEvent } from "../types/alert";

interface DetectionSocketState {
  connected: boolean;
  latestAlert: FodDetectedEvent | null;
  latestEvent: AlertEvent | null;
  error: string | null;
}

const RECONNECT_MS = 2000;

export function useDetectionSocket(enabled = true): DetectionSocketState {
  const [state, setState] = useState<DetectionSocketState>({
    connected: false,
    latestAlert: null,
    latestEvent: null,
    error: null
  });
  const reconnectTimer = useRef<number | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let closedByHook = false;

    function connect() {
      const socket = new WebSocket(EVENTS_WS_URL);
      socketRef.current = socket;

      socket.onopen = () => {
        setState((current) => ({ ...current, connected: true, error: null }));
      };

      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as AlertEvent;
        setState((current) => ({
          ...current,
          latestEvent: event,
          latestAlert:
            event.type === "fod.detected"
              ? (event as AlertEvent<FodDetectedData>)
              : current.latestAlert
        }));
      };

      socket.onerror = () => {
        setState((current) => ({
          ...current,
          connected: false,
          error: "WebSocket event channel unavailable"
        }));
      };

      socket.onclose = () => {
        setState((current) => ({ ...current, connected: false }));
        if (!closedByHook) {
          reconnectTimer.current = window.setTimeout(connect, RECONNECT_MS);
        }
      };
    }

    connect();

    return () => {
      closedByHook = true;
      if (reconnectTimer.current !== null) {
        window.clearTimeout(reconnectTimer.current);
      }
      socketRef.current?.close();
    };
  }, [enabled]);

  return state;
}
