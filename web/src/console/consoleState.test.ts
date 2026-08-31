import { describe, expect, it } from "vitest";

import { formatWhen, parseConsoleState } from "./consoleState";

const payload = JSON.stringify({
  addresses: ["192.168.1.50"],
  port: 8477,
  url: "http://192.168.1.50:8477/?t=abc",
  connected: 1,
  caps: { audio: true, media: true, clipboard: false },
  service: { active: true, enabled: true },
  events: [{ kind: "info", message: "phone connected", at: 1788000000 }],
});

describe("parseConsoleState", () => {
  it("reads a full payload", () => {
    const state = parseConsoleState(payload);
    expect(state?.port).toBe(8477);
    expect(state?.connected).toBe(1);
    expect(state?.service.active).toBe(true);
    expect(state?.events[0].message).toBe("phone connected");
  });

  it("survives an agent with no network address", () => {
    const state = parseConsoleState(JSON.stringify({
      addresses: [], port: 8477, url: "", connected: 0,
      caps: { audio: false, media: false, clipboard: false },
      service: { active: false, enabled: false }, events: [],
    }));
    expect(state?.url).toBe("");
    expect(state?.addresses).toEqual([]);
  });

  it("rejects nonsense", () => {
    expect(parseConsoleState("not json")).toBeNull();
    expect(parseConsoleState("[]")).toBeNull();
    expect(parseConsoleState("")).toBeNull();
  });
});

describe("formatWhen", () => {
  it("formats a timestamp as a clock time", () => {
    expect(formatWhen(1788000000)).toMatch(/^\d{1,2}:\d{2}/);
  });

  it("refuses nonsense", () => {
    expect(formatWhen(Number.NaN)).toBe("");
  });
});

const full = {
  addresses: ["192.168.1.50"], port: 8477, url: "http://192.168.1.50:8477/?t=abc",
  connected: 1, caps: { audio: true, media: true, clipboard: false },
  service: { active: true, enabled: true }, events: [],
};

describe("parseConsoleState rejects payloads the page cannot render", () => {
  it.each(["caps", "service", "events", "url", "connected"] as const)(
    "refuses a payload missing %s",
    (key) => {
      const partial = { ...full };
      delete (partial as Record<string, unknown>)[key];
      expect(parseConsoleState(JSON.stringify(partial))).toBeNull();
    },
  );

  it("refuses events that are not a list", () => {
    expect(parseConsoleState(JSON.stringify({ ...full, events: "none" }))).toBeNull();
  });

  it("refuses caps that are not an object", () => {
    expect(parseConsoleState(JSON.stringify({ ...full, caps: [] }))).toBeNull();
  });

  it("still accepts a complete payload", () => {
    expect(parseConsoleState(JSON.stringify(full))).not.toBeNull();
  });
});

describe("formatWhen", () => {
  it("returns nothing for a timestamp outside the calendar", () => {
    expect(formatWhen(1e15)).toBe("");
    expect(formatWhen(1e23)).toBe("");
  });
});
