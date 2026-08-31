import { describe, expect, it } from "vitest";

import { ScrollAccumulator, accelerate, isTap } from "./gestures";

describe("accelerate", () => {
  it("moves further for a faster swipe", () => {
    expect(accelerate(20, 1)).toBeGreaterThan(accelerate(2, 1));
  });

  it("scales with the sensitivity setting", () => {
    expect(accelerate(10, 2)).toBeGreaterThan(accelerate(10, 1));
  });

  it("stays bounded so a flick cannot throw the cursor across the desk", () => {
    // The agent refuses moves over 4000, and a refused move is a lost one.
    expect(accelerate(10_000, 2.4)).toBeLessThan(4000);
  });

  it("never inverts direction", () => {
    expect(accelerate(0, 1)).toBeGreaterThanOrEqual(0);
  });
});

describe("ScrollAccumulator", () => {
  it("holds back fractions until a whole notch is due", () => {
    const acc = new ScrollAccumulator();
    expect(acc.add(4, false)).toBe(0);
    expect(acc.add(4, false)).toBe(0);
    expect(acc.add(4, false)).not.toBe(0);
  });

  it("keeps the remainder between calls", () => {
    const acc = new ScrollAccumulator();
    let total = 0;
    for (let i = 0; i < 100; i += 1) {
      total += acc.add(1.2, false);
    }
    expect(Math.abs(total)).toBeGreaterThan(9);
  });

  it("flips direction for natural scrolling", () => {
    const normal = new ScrollAccumulator();
    const natural = new ScrollAccumulator();
    expect(Math.sign(normal.add(40, false))).toBe(-Math.sign(natural.add(40, true)));
  });
});

describe("isTap", () => {
  it("accepts a quick still touch", () => {
    expect(isTap(120, 4)).toBe(true);
  });

  it("refuses a slow touch", () => {
    expect(isTap(900, 2)).toBe(false);
  });

  it("refuses a touch that travelled", () => {
    expect(isTap(120, 40)).toBe(false);
  });
});
