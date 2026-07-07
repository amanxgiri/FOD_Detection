export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/api/v1/ws";
export const EVENTS_WS_URL = `${WS_BASE_URL}/events`;
