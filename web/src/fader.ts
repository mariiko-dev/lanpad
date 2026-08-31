export const SEND_INTERVAL_MS = 60;
export const LOCK_AFTER_RELEASE_MS = 400;

/** How close an incoming value must land to count as our seek arriving. */
export const SETTLE_TOLERANCE = 1.5;
/** Ceiling on waiting for confirmation, so a player that never seeks cannot freeze the knob. */
export const SETTLE_TIMEOUT_MS = 3000;

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
  private awaiting: { expected: number; tolerance: number; since: number } | null = null;

  grab(): void {
    this.held = true;
  }

  release(now: number): void {
    this.held = false;
    this.releasedAt = now;
    this.awaiting = null;
  }

  /**
   * Hold the knob until the computer confirms the value we asked for.
   *
   * A seek is not instant — the player hunts for a keyframe and refills its
   * buffer — so a fixed delay either snaps the knob back to the old position
   * or freezes it needlessly. Waiting for the value itself does neither.
   */
  commit(now: number, expected: number, tolerance: number): void {
    this.held = false;
    this.releasedAt = now;
    this.awaiting = { expected, tolerance, since: now };
  }

  /** `incoming` is required only while awaiting confirmation. */
  accepts(now: number, incoming?: number): boolean {
    if (this.held) {
      return false;
    }
    if (this.awaiting) {
      if (now - this.awaiting.since > SETTLE_TIMEOUT_MS) {
        this.awaiting = null;
        return true;
      }
      if (incoming === undefined) {
        return false;
      }
      if (Math.abs(incoming - this.awaiting.expected) <= this.awaiting.tolerance) {
        this.awaiting = null;
        return true;
      }
      return false;
    }
    return now - this.releasedAt > LOCK_AFTER_RELEASE_MS;
  }
}
