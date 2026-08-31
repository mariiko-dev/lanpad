import { describe, expect, it } from "vitest";

import { canTypeDirectly, namedKeyFor } from "./keymap";

describe("namedKeyFor", () => {
  it("maps the keys the agent knows", () => {
    expect(namedKeyFor("Escape")).toBe("escape");
    expect(namedKeyFor("ArrowUp")).toBe("up");
    expect(namedKeyFor("Backspace")).toBe("backspace");
  });

  it("returns null for ordinary characters", () => {
    expect(namedKeyFor("a")).toBeNull();
    expect(namedKeyFor("Ж")).toBeNull();
  });
});

describe("canTypeDirectly", () => {
  it("accepts what the agent's layout covers", () => {
    expect(canTypeDirectly("hello world!")).toBe(true);
  });

  it("refuses what has to go through the clipboard", () => {
    // Cyrillic and emoji cannot be typed key by key on a US layout.
    expect(canTypeDirectly("привет")).toBe(false);
    expect(canTypeDirectly("🎧")).toBe(false);
    expect(canTypeDirectly("mixed привет")).toBe(false);
  });

  it("refuses an empty string", () => {
    expect(canTypeDirectly("")).toBe(false);
  });
});
