const websocketProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const backendWsOrigin =
  import.meta.env.VITE_WS_ORIGIN ??
  `${websocketProtocol}//${window.location.hostname || "localhost"}:8000`;

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? `${backendWsOrigin}/api/v1/ws`;
export const EVENTS_WS_URL = `${WS_BASE_URL}/events`;
