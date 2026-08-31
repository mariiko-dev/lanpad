import { describe, expect, it } from "vitest";

import { flushMethod } from "./typing";

describe("flushMethod", () => {
  it("pastes an empty buffer", () => {
    // The flush guard never calls it empty, but the answer stays defined.
    expect(flushMethod("")).toBe("paste");
  });

  it("types a Latin-only buffer", () => {
    expect(flushMethod("hello world")).toBe("type");
  });

  it("pastes a Cyrillic-only buffer", () => {
    expect(flushMethod("привет")).toBe("paste");
  });

  it("pastes a mixed buffer so the order is preserved", () => {
    expect(flushMethod("привет hello")).toBe("paste");
  });

  it("pastes a buffer with emoji", () => {
    expect(flushMethod("nice 🎧")).toBe("paste");
  });

  it("types a very long Latin buffer", () => {
    expect(flushMethod("a".repeat(500))).toBe("type");
  });
});
