import { describe, expect, it } from "vitest";

import { flushMethod } from "./typing";

describe("flushMethod", () => {
  it("pastes an empty buffer", () => {
    // The flush guard never calls it empty, but the answer stays defined.
    expect(flushMethod("")).toBe("paste");
  });

  it("pastes a Latin-only buffer", () => {
    expect(flushMethod("hello world")).toBe("paste");
  });

  it("pastes a Cyrillic-only buffer", () => {
    expect(flushMethod("привет")).toBe("paste");
  });

  it("pastes a mixed buffer", () => {
    expect(flushMethod("привет hello")).toBe("paste");
  });

  it("pastes a buffer with emoji", () => {
    expect(flushMethod("nice 🎧")).toBe("paste");
  });

  it("pastes a very long buffer", () => {
    expect(flushMethod("a".repeat(500))).toBe("paste");
  });

  it("never sends latin text as key codes", () => {
    // Key codes go through the computer's layout: on a machine set to
    // Russian, "hello" typed as key codes arrives as "руддщ".
    expect(flushMethod("hello")).toBe("paste");
  });
});
