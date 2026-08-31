/** Types and helpers for the wire format the agent speaks. */

export interface AudioState {
  volume: number | null;
  muted: boolean;
}

export interface MediaState {
  playing: boolean;
  title: string;
  artist: string;
  art: string | null;
  position: number;
  duration: number;
  canSeek: boolean;
}

export interface Capabilities {
  audio: boolean;
  media: boolean;
  clipboard: boolean;
}

export interface AgentState {
  audio: AudioState | null;
  media: MediaState | null;
  caps: Capabilities;
}

/** One outgoing event. The agent validates these again on its side. */
export type Event =
  | ["m", number, number]
  | ["w", number]
  | ["bd" | "bu", "l" | "r" | "m"]
  | ["click", "l" | "r" | "m"]
  | ["tap", string]
  | ["kd" | "ku", string]
  | ["combo", string[]]
  | ["type", string]
  | ["paste" | "tpaste", string]
  | ["vol", number]
  | ["volset", number]
  | ["volmute"]
  | ["media", "play" | "next" | "prev"]
  | ["seek", number];

/** The agent refuses packets larger than this, so we never build one. */
export const MAX_EVENTS = 512;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseState(raw: string): AgentState | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(payload) || payload.type !== "state" || !isRecord(payload.caps)) {
    return null;
  }
  return {
    audio: isRecord(payload.audio) ? (payload.audio as unknown as AudioState) : null,
    media: isRecord(payload.media) ? (payload.media as unknown as MediaState) : null,
    caps: payload.caps as unknown as Capabilities,
  };
}

/**
 * A cover URL comes from whatever player is running on the machine, so it
 * is not trusted. Only real image sources and our own proxy path pass.
 */
export function safeArtUrl(art: string | null): string | null {
  if (!art) {
    return null;
  }
  if (art.startsWith("/art?id=")) {
    return art;
  }
  return /^https?:\/\/[^/]/.test(art) ? art : null;
}
