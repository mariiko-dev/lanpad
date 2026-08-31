import { describe, expect, it } from "vitest";

import { manifestHref } from "./manifest";

describe("manifestHref", () => {
  it("carries the token", () => {
    // The agent answers 403 without it, and add-to-home-screen then fails.
    expect(manifestHref("abc123")).toBe("/manifest.webmanifest?t=abc123");
  });

  it("escapes the token", () => {
    expect(manifestHref("a+b")).toBe("/manifest.webmanifest?t=a%2Bb");
  });

  it("returns an empty string without a token", () => {
    expect(manifestHref("")).toBe("");
  });
});
