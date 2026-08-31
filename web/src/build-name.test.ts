import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Copied verbatim from the agent (http.py `_HASHED_NAME`). A name that
// does not match gets `no-cache`, so an upgrade would never reach a
// paired phone without clearing site data.
const AGENT_HASHED_NAME = /-[0-9a-f]{6,}\.[a-z0-9]+$/;

const built = join(__dirname, "..", "..", "src", "lanpad", "web");

describe("build output", () => {
  it("emits both pages", () => {
    expect(existsSync(join(built, "index.html"))).toBe(true);
    expect(existsSync(join(built, "console.html"))).toBe(true);
  });

  it("emits names the agent will cache forever", () => {
    const files = readdirSync(join(built, "assets")).filter((n) => /\.(js|css)$/.test(n));
    expect(files.length).toBeGreaterThan(0);
    for (const name of files) {
      expect(name).toMatch(AGENT_HASHED_NAME);
    }
  });
});
