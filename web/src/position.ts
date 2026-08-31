/**
 * Track position between updates.
 *
 * The agent pushes position rarely on purpose — a packet a second for a
 * number the phone can compute itself would be pure latency.
 */
export function interpolatePosition(
  base: number,
  playing: boolean,
  elapsedMs: number,
  duration: number,
): number {
  const advanced = playing ? base + elapsedMs / 1000 : base;
  const capped = duration > 0 ? Math.min(advanced, duration) : advanced;
  return Math.max(capped, 0);
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }
  const whole = Math.floor(seconds);
  const s = whole % 60;
  const m = Math.floor(whole / 60) % 60;
  const h = Math.floor(whole / 3600);
  const pad = (value: number): string => String(value).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}
