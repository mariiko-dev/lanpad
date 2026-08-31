import { describe, expect, it } from "vitest";

import { DEFAULT_ACCENT, dominantColor, readableAccent, themeVariables } from "./theme";

function pixels(...rgba: number[]): Uint8ClampedArray {
  return new Uint8ClampedArray(rgba);
}

describe("dominantColor", () => {
  it("averages the pixels it is given", () => {
    const [r, g, b] = dominantColor(pixels(200, 0, 0, 255, 0, 0, 0, 255));
    expect(r).toBeGreaterThan(g);
    expect(r).toBeGreaterThan(b);
  });

  it("ignores transparent pixels", () => {
    // A cover padded with transparency would otherwise read as black.
    const [r] = dominantColor(pixels(255, 0, 0, 255, 0, 0, 0, 0));
    expect(r).toBeGreaterThan(200);
  });

  it("returns black for an empty or fully transparent input", () => {
    expect(dominantColor(pixels())).toEqual([0, 0, 0]);
    expect(dominantColor(pixels(255, 255, 255, 0))).toEqual([0, 0, 0]);
  });
});

describe("readableAccent", () => {
  it("lifts a dark cover to something visible on black", () => {
    // A maroon fill on a black track is invisible; the fader would look
    // empty at every volume.
    const lifted = readableAccent([40, 0, 10]);
    expect(lifted).toMatch(/^hsl\(/);
    const lightness = Number(lifted.match(/([\d.]+)%\)$/)?.[1]);
    expect(lightness).toBeGreaterThanOrEqual(45);
  });

  it("lifts a washed-out cover to something with colour", () => {
    const lifted = readableAccent([130, 128, 129]);
    const saturation = Number(lifted.match(/,\s*([\d.]+)%/)?.[1]);
    expect(saturation).toBeGreaterThanOrEqual(35);
  });

  it("leaves an already vivid cover close to itself", () => {
    const vivid = readableAccent([196, 77, 255]);
    const lightness = Number(vivid.match(/([\d.]+)%\)$/)?.[1]);
    expect(lightness).toBeLessThan(80);
  });

  it("never returns a colour that would vanish", () => {
    for (const rgb of [[0, 0, 0], [255, 255, 255], [1, 1, 1]] as const) {
      const lightness = Number(readableAccent(rgb).match(/([\d.]+)%\)$/)?.[1]);
      expect(lightness).toBeGreaterThanOrEqual(45);
      expect(lightness).toBeLessThanOrEqual(75);
    }
  });
});

describe("themeVariables", () => {
  it("gives the calm mode no glow", () => {
    expect(themeVariables(DEFAULT_ACCENT, "calm")["--glow-opacity"]).toBe("0");
  });

  it("gives the normal mode a glow but plain panels", () => {
    const normal = themeVariables(DEFAULT_ACCENT, "normal");
    expect(Number(normal["--glow-opacity"])).toBeGreaterThan(0);
    expect(normal["--panel-tint"]).toBe("0");
  });

  it("tints panels only in the rich mode", () => {
    expect(Number(themeVariables(DEFAULT_ACCENT, "rich")["--panel-tint"])).toBeGreaterThan(0);
  });

  it("always carries the accent", () => {
    for (const mode of ["calm", "normal", "rich"] as const) {
      expect(themeVariables("hsl(280, 80%, 60%)", mode)["--accent"]).toBe("hsl(280, 80%, 60%)");
    }
  });
});
