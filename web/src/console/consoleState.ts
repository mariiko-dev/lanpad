export interface ConsoleEvent {
  kind: string;
  message: string;
  at: number;
}

export interface ConsoleState {
  addresses: string[];
  port: number;
  url: string;
  connected: number;
  caps: { audio: boolean; media: boolean; clipboard: boolean };
  service: { active: boolean; enabled: boolean };
  events: ConsoleEvent[];
}

export function parseConsoleState(raw: string): ConsoleState | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return null;
  }
  const value = payload as Partial<ConsoleState>;
  if (typeof value.port !== "number" || !Array.isArray(value.addresses)) {
    return null;
  }
  return value as ConsoleState;
}

export function formatWhen(at: number): string {
  if (!Number.isFinite(at)) {
    return "";
  }
  return new Date(at * 1000).toLocaleTimeString();
}
