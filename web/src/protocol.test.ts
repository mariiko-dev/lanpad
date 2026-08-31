import { describe, expect, it } from "vitest";

import { parseState, safeArtUrl } from "./protocol";

const full = JSON.stringify({
  type: "state",
  audio: { volume: 62, muted: false },
  media: {
    playing: true, title: "Bohemian Rhapsody", artist: "Queen",
    art: "/art?id=abc", position: 134.2, duration: 355, canSeek: true,
  },
  caps: { audio: true, media: true, clipboard: true },
});

describe("parseState", () => {
  it("reads a full state message", () => {
    const state = parseState(full);
    expect(state?.audio?.volume).toBe(62);
    expect(state?.media?.title).toBe("Bohemian Rhapsody");
    expect(state?.media?.canSeek).toBe(true);
    expect(state?.caps.clipboard).toBe(true);
  });

  it("accepts null audio and media", () => {
    const state = parseState(JSON.stringify({
      type: "state", audio: null, media: null,
      caps: { audio: false, media: false, clipboard: false },
    }));
    expect(state?.audio).toBeNull();
    expect(state?.media).toBeNull();
  });

  it("rejects anything that is not a state message", () => {
    expect(parseState("not json")).toBeNull();
    expect(parseState(JSON.stringify({ type: "other" }))).toBeNull();
    expect(parseState(JSON.stringify([1, 2, 3]))).toBeNull();
    expect(parseState("")).toBeNull();
  });
});

describe("safeArtUrl", () => {
  it("keeps http and https covers", () => {
    expect(safeArtUrl("https://cdn.example/a.jpg")).toBe("https://cdn.example/a.jpg");
    expect(safeArtUrl("http://cdn.example/a.jpg")).toBe("http://cdn.example/a.jpg");
  });

  it("keeps our own proxied path", () => {
    expect(safeArtUrl("/art?id=abc")).toBe("/art?id=abc");
  });

  it("refuses everything else", () => {
    // A local player controls this string; it must not become a page URL.
    expect(safeArtUrl("javascript:alert(1)")).toBeNull();
    expect(safeArtUrl("data:image/png;base64,AAAA")).toBeNull();
    expect(safeArtUrl("file:///etc/passwd")).toBeNull();
    expect(safeArtUrl("//evil.example/a.jpg")).toBeNull();
    expect(safeArtUrl("/other/path")).toBeNull();
    expect(safeArtUrl(null)).toBeNull();
    expect(safeArtUrl("")).toBeNull();
  });
});
