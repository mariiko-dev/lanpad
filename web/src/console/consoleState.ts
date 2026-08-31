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

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseConsoleState(raw: string): ConsoleState | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isObject(payload)) {
    return null;
  }
  const value = payload as Partial<ConsoleState>;
  // Every field the page renders is checked here. A payload that passes
  // this gate and still breaks the render would leave a white window with
  // no way back, because a render failure is not something the polling
  // loop can catch.
  if (
    typeof value.port !== "number"
    || !Array.isArray(value.addresses)
    || typeof value.url !== "string"
    || typeof value.connected !== "number"
    || !isObject(value.caps)
    || !isObject(value.service)
    || !Array.isArray(value.events)
  ) {
    return null;
  }
  return value as ConsoleState;
}

export function formatWhen(at: number): string {
  if (!Number.isFinite(at)) {
    return "";
  }
  const when = new Date(at * 1000);
  return Number.isNaN(when.getTime()) ? "" : when.toLocaleTimeString();
}
