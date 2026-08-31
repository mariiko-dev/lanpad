import type { Saturation } from "./settings";

export const DEFAULT_ACCENT = "hsl(265, 70%, 62%)";

const MIN_LIGHTNESS = 45;
const MAX_LIGHTNESS = 75;
const MIN_SATURATION = 35;

/** Average the visible pixels of a downscaled cover. */
export function dominantColor(pixels: Uint8ClampedArray): [number, number, number] {
  let r = 0;
  let g = 0;
  let b = 0;
  let counted = 0;
  for (let i = 0; i + 3 < pixels.length; i += 4) {
    const alpha = pixels[i + 3];
    if (alpha === 0) {
      continue;
    }
    r += pixels[i];
    g += pixels[i + 1];
    b += pixels[i + 2];
    counted += 1;
  }
  if (counted === 0) {
    return [0, 0, 0];
  }
  return [Math.round(r / counted), Math.round(g / counted), Math.round(b / counted)];
}

function toHsl([r, g, b]: readonly [number, number, number]): [number, number, number] {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (delta === 0) {
    return [0, 0, lightness * 100];
  }
  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue: number;
  if (max === rn) {
    hue = ((gn - bn) / delta) % 6;
  } else if (max === gn) {
    hue = (bn - rn) / delta + 2;
  } else {
    hue = (rn - gn) / delta + 4;
  }
  return [((hue * 60) + 360) % 360, saturation * 100, lightness * 100];
}

/**
 * Push a cover's colour into a range that stays visible on black.
 *
 * A dark or washed-out cover would otherwise paint a fader that looks
 * empty at every value, which reads as broken rather than subtle.
 */
export function readableAccent(rgb: readonly [number, number, number]): string {
  const [hue, saturation, lightness] = toHsl(rgb);
  const s = Math.max(saturation, MIN_SATURATION);
  const l = Math.min(Math.max(lightness, MIN_LIGHTNESS), MAX_LIGHTNESS);
  return `hsl(${Math.round(hue)}, ${Math.round(s)}%, ${Math.round(l)}%)`;
}

/**
 * CSS variables for one saturation mode.
 *
 * The glow is a static layer and the panel tint is a flat fill: neither
 * repaints while a finger moves, which is what keeps the pad responsive.
 */
export function themeVariables(
  accent: string,
  saturation: Saturation,
): Record<string, string> {
  const glow = { calm: "0", normal: "0.5", rich: "0.34" }[saturation];
  const tint = { calm: "0", normal: "0", rich: "0.14" }[saturation];
  return {
    "--accent": accent,
    "--glow-opacity": glow,
    "--panel-tint": tint,
  };
}
