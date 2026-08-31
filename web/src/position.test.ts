import { describe, expect, it } from "vitest";

import { formatTime, interpolatePosition } from "./position";

describe("interpolatePosition", () => {
  it("advances while playing", () => {
    // The agent sends position rarely; the phone fills the gap itself
    // rather than asking every second.
    expect(interpolatePosition(100, true, 2000, 355)).toBeCloseTo(102, 3);
  });

  it("stands still while paused", () => {
    expect(interpolatePosition(100, false, 5000, 355)).toBe(100);
  });

  it("never runs past the end of the track", () => {
    expect(interpolatePosition(350, true, 60_000, 355)).toBe(355);
  });

  it("never goes negative", () => {
    expect(interpolatePosition(0, true, 0, 355)).toBe(0);
  });

  it("tolerates an unknown duration", () => {
    expect(interpolatePosition(10, true, 1000, 0)).toBeCloseTo(11, 3);
  });
});

describe("formatTime", () => {
  it("formats minutes and seconds", () => {
    expect(formatTime(134)).toBe("2:14");
    expect(formatTime(5)).toBe("0:05");
    expect(formatTime(0)).toBe("0:00");
  });

  it("formats past an hour", () => {
    expect(formatTime(3725)).toBe("1:02:05");
  });

  it("refuses to show nonsense", () => {
    expect(formatTime(-5)).toBe("0:00");
    expect(formatTime(Number.NaN)).toBe("0:00");
    expect(formatTime(Number.POSITIVE_INFINITY)).toBe("0:00");
  });
});
