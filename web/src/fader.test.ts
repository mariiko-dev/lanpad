import { describe, expect, it } from "vitest";

import { FaderLock, LOCK_AFTER_RELEASE_MS, valueFromPosition } from "./fader";

const box = { left: 100, width: 200 };

describe("valueFromPosition", () => {
  it("maps the ends of the track", () => {
    expect(valueFromPosition(100, box, 0, 100)).toBe(0);
    expect(valueFromPosition(300, box, 0, 100)).toBe(100);
  });

  it("maps the middle", () => {
    expect(valueFromPosition(200, box, 0, 100)).toBe(50);
  });

  it("clamps outside the track", () => {
    expect(valueFromPosition(0, box, 0, 100)).toBe(0);
    expect(valueFromPosition(9999, box, 0, 100)).toBe(100);
  });

  it("works for an arbitrary range, like track position", () => {
    expect(valueFromPosition(200, box, 0, 355)).toBeCloseTo(177.5, 1);
  });

  it("survives a zero-width track", () => {
    expect(valueFromPosition(50, { left: 0, width: 0 }, 0, 100)).toBe(0);
  });
});

describe("FaderLock", () => {
  it("ignores incoming state while the finger is down", () => {
    const lock = new FaderLock();
    lock.grab();
    expect(lock.accepts(1000)).toBe(false);
  });

  it("keeps ignoring briefly after release", () => {
    // A packet sent before our change can still be in flight; applying it
    // would snap the knob back under the user's finger.
    const lock = new FaderLock();
    lock.grab();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS - 50)).toBe(false);
  });

  it("accepts state once the grace period passes", () => {
    const lock = new FaderLock();
    lock.grab();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS + 1)).toBe(true);
  });

  it("accepts state when it was never touched", () => {
    expect(new FaderLock().accepts(0)).toBe(true);
  });
});

describe("FaderLock", () => {
  it("can always be released, even without a matching grab", () => {
    const lock = new FaderLock();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS + 1)).toBe(true);
  });
});
