import { describe, expect, it } from "vitest";

import { MAX_EVENTS } from "./protocol";
import { readToken } from "./token";
import { EventQueue } from "./transport";

describe("readToken", () => {
  it("reads the token the QR link carries", () => {
    expect(readToken("?t=abc123")).toBe("abc123");
  });

  it("decodes percent escapes", () => {
    expect(readToken("?t=a%2Bb")).toBe("a+b");
  });

  it("returns empty when absent", () => {
    expect(readToken("")).toBe("");
    expect(readToken("?other=1")).toBe("");
  });
});

describe("EventQueue", () => {
  it("hands events over in order", () => {
    const queue = new EventQueue();
    queue.push(["m", 1, 2]);
    queue.push(["click", "l"]);
    expect(queue.drain()).toEqual([["m", 1, 2], ["click", "l"]]);
  });

  it("empties on drain", () => {
    const queue = new EventQueue();
    queue.push(["w", 1]);
    queue.drain();
    expect(queue.drain()).toEqual([]);
  });

  it("drops the oldest events rather than growing without bound", () => {
    // A stalled connection during a long drag must not build a packet the
    // agent will refuse outright — it refuses anything over MAX_EVENTS,
    // which would throw away the recent moves along with the stale ones.
    const queue = new EventQueue();
    for (let i = 0; i < MAX_EVENTS + 50; i += 1) {
      queue.push(["m", i, 0]);
    }
    const drained = queue.drain();
    expect(drained.length).toBe(MAX_EVENTS);
    expect(drained[drained.length - 1]).toEqual(["m", MAX_EVENTS + 49, 0]);
  });

  it("reports its size", () => {
    const queue = new EventQueue();
    expect(queue.size()).toBe(0);
    queue.push(["w", 1]);
    expect(queue.size()).toBe(1);
  });
});
