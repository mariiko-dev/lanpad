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
  const boosted = factor * (1 + Math.min(distance * 0.06, 4));
  return Math.min(boosted, MAX_STEP);
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
