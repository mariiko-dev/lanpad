import { describe, expect, it } from "vitest";

import { en } from "./en";
import { pickLanguage, strings } from "./index";
import { ru } from "./ru";

describe("pickLanguage", () => {
  it("picks russian for russian speakers", () => {
    expect(pickLanguage(["ru-RU", "en-US"])).toBe("ru");
    expect(pickLanguage(["ru"])).toBe("ru");
  });

  it("falls back to english for everything else", () => {
    expect(pickLanguage(["en-GB"])).toBe("en");
    expect(pickLanguage(["de-DE"])).toBe("en");
    expect(pickLanguage([])).toBe("en");
  });

  it("honours the first understood language, not the first listed", () => {
    expect(pickLanguage(["de-DE", "ru-RU", "en-US"])).toBe("ru");
  });
});

describe("dictionaries", () => {
  it("cover the same keys", () => {
    expect(Object.keys(ru).sort()).toEqual(Object.keys(en).sort());
  });

  it("have no empty strings", () => {
    for (const dict of [en, ru]) {
      for (const [key, value] of Object.entries(dict)) {
        expect(value, key).not.toBe("");
      }
    }
  });

  it("keep russian labels short enough for buttons", () => {
    // Russian runs about a third longer than English; a label that
    // overflows on the narrowest phone is a broken layout, not a detail.
    const buttonKeys = ["click", "rightClick", "paste", "pasteTerminal", "done"] as const;
    for (const key of buttonKeys) {
      expect(ru[key].length, key).toBeLessThanOrEqual(14);
    }
  });

  it("resolves a dictionary by language", () => {
    expect(strings("ru")).toBe(ru);
    expect(strings("en")).toBe(en);
  });
});
