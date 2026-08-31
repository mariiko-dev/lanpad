export const SEND_INTERVAL_MS = 60;
export const LOCK_AFTER_RELEASE_MS = 400;

/**
 * Whether a drag sample should reach the computer right now.
 *
 * Volume must follow the finger, so a normal drag streams on a timer. A
 * seek must not: every request makes the player jump and refill its
 * buffer, so a drag's worth of them fights the finger and stutters the
 * picture. With `commitOnly` only the release — where the finger lands —
 * is sent.
 */
export function shouldSend(
  commitOnly: boolean,
  release: boolean,
  now: number,
  lastSentAt: number,
): boolean {
  if (commitOnly) {
    return release;
  }
  return release || now - lastSentAt >= SEND_INTERVAL_MS;
}

/** Where along the track the finger is, in the fader's own units. */
export function valueFromPosition(
  clientX: number,
  box: { left: number; width: number },
  min: number,
  max: number,
): number {
  if (box.width <= 0) {
    return min;
  }
  const share = Math.min(Math.max((clientX - box.left) / box.width, 0), 1);
  return min + share * (max - min);
}

/**
 * Decides whether incoming state may move the knob.
 *
 * While a finger is on the fader the knob obeys the finger alone, and for
 * a moment after release too: a packet sent before our change can still
 * arrive, and applying it would snap the knob backwards.
 */
export class FaderLock {
  private held = false;
  private releasedAt = -Infinity;

  grab(): void {
    this.held = true;
  }

  release(now: number): void {
    this.held = false;
    this.releasedAt = now;
  }

  accepts(now: number): boolean {
    return !this.held && now - this.releasedAt > LOCK_AFTER_RELEASE_MS;
  }
}
