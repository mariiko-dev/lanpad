const SCROLL_SCALE = 0.09;
const TAP_MAX_MS = 240;
const TAP_MAX_TRAVEL = 12;
const MAX_STEP = 3900; // the agent refuses anything past 4000

/**
 * Pointer acceleration.
 *
 * A slow drag should land on a pixel; a fast one should cross the screen.
 * The result is capped below the agent's own limit, because a refused
 * move is a lost move, not a clamped one.
 */
export function accelerate(distance: number, factor: number): number {
  const travelled = Math.max(0, distance);
  const boosted = factor * (1 + Math.min(travelled * 0.06, 4));
  return Math.min(boosted, MAX_STEP);
}

// The agent refuses anything past these and drops the whole event, so a
// value clamped here is a move that lands, not a move that vanishes.
export const MAX_MOVE = 4000;
export const MAX_WHEEL = 200;

export function clampMove(value: number): number {
  return Math.max(-MAX_MOVE, Math.min(MAX_MOVE, Math.round(value)));
}

export function clampWheel(value: number): number {
  return Math.max(-MAX_WHEEL, Math.min(MAX_WHEEL, Math.trunc(value)));
}

/** Turns finger travel into whole wheel notches, keeping the remainder. */
export class ScrollAccumulator {
  private remainder = 0;

  add(delta: number, natural: boolean): number {
    this.remainder += delta * SCROLL_SCALE * (natural ? 1 : -1);
    const whole = Math.trunc(this.remainder);
    this.remainder -= whole;
    // `+ 0` normalises the -0 that Math.trunc yields on small negative
    // sums, so callers may compare the result against 0 with Object.is.
    return whole + 0;
  }
}

export function isTap(elapsedMs: number, travelled: number): boolean {
  return elapsedMs < TAP_MAX_MS && travelled < TAP_MAX_TRAVEL;
}

export const SCROLL_STRIP_MIN_PX = 28;
const SCROLL_STRIP_SHARE = 0.1;

/**
 * Is this touch in the edge strip that scrolls with one finger?
 *
 * A tenth of the pad is right on a large phone and unhittable on a small
 * one, so the strip never gets narrower than a thumb.
 */
export function isInScrollStrip(x: number, box: { left: number; width: number }): boolean {
  const stripWidth = Math.max(box.width * SCROLL_STRIP_SHARE, SCROLL_STRIP_MIN_PX);
  return x >= box.left + box.width - stripWidth;
}
