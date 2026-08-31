import { describe, expect, it } from "vitest";

import {
  FaderLock,
  LOCK_AFTER_RELEASE_MS,
  SETTLE_TIMEOUT_MS,
  SETTLE_TOLERANCE,
  shouldSend,
  valueFromPosition,
} from "./fader";

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

describe("shouldSend", () => {
  const stream = (commitOnly: boolean, points: number[]): number[] => {
    const sent: number[] = [];
    let lastSentAt = -Infinity;
    points.forEach((value, i) => {
      const release = i === points.length - 1;
      const now = i * 20; // faster than SEND_INTERVAL_MS between samples
      if (shouldSend(commitOnly, release, now, lastSentAt)) {
        lastSentAt = now;
        sent.push(value);
      }
    });
    return sent;
  };

  it("streams a volume drag along the way", () => {
    const sent = stream(false, [10, 20, 30, 40, 50, 60, 70, 80]);
    expect(sent.length).toBeGreaterThan(1);
    expect(sent.at(-1)).toBe(80);
  });

  it("sends a seek once, where the finger lands", () => {
    expect(stream(true, [10, 20, 30, 40])).toEqual([40]);
  });

  it("still sends on release even a lone tap", () => {
    expect(stream(true, [42])).toEqual([42]);
  });
});

describe("FaderLock.commit", () => {
  it("holds the knob until an incoming value lands near the one we asked for", () => {
    const lock = new FaderLock();
    lock.grab();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    // The old position keeps arriving while the player hunts for a keyframe.
    expect(lock.accepts(1200, 40)).toBe(false);
    expect(lock.accepts(1500, 30)).toBe(false);
    // Our seek arrives.
    expect(lock.accepts(1800, 120.8)).toBe(true);
  });

  it("keeps holding while the finger is back on the knob", () => {
    const lock = new FaderLock();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    lock.grab();
    expect(lock.accepts(1200, 120)).toBe(false);
  });

  it("does not accept a value outside the tolerance", () => {
    const lock = new FaderLock();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    expect(lock.accepts(1100, 120 + SETTLE_TOLERANCE + 0.5)).toBe(false);
  });

  it("does not accept while awaiting if no incoming value is offered", () => {
    const lock = new FaderLock();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    expect(lock.accepts(1100)).toBe(false);
  });

  it("gives up waiting once the ceiling passes, so a player that never seeks cannot freeze the knob", () => {
    const lock = new FaderLock();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    expect(lock.accepts(1000 + SETTLE_TIMEOUT_MS + 1)).toBe(true);
  });

  it("stops awaiting once the value arrives, so later state flows again", () => {
    const lock = new FaderLock();
    lock.commit(1000, 120, SETTLE_TOLERANCE);
    expect(lock.accepts(1200, 120)).toBe(true);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS + 1, 55)).toBe(true);
  });

  it("leaves the plain release path unchanged for the volume fader", () => {
    const lock = new FaderLock();
    lock.grab();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS - 50, 40)).toBe(false);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS + 1, 40)).toBe(true);
  });
});
