import { describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from "./settings";

function memoryStorage(seed?: string): Storage {
  const map = new Map<string, string>();
  if (seed !== undefined) {
    map.set("lanpad", seed);
  }
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
    clear: () => map.clear(),
    key: () => null,
    length: 0,
  } as unknown as Storage;
}

describe("loadSettings", () => {
  it("takes the language from the phone on first run", () => {
    expect(loadSettings(memoryStorage(), ["ru-RU"]).language).toBe("ru");
    expect(loadSettings(memoryStorage(), ["de-DE"]).language).toBe("en");
  });

  it("prefers a stored choice over the phone language", () => {
    const stored = JSON.stringify({ ...DEFAULT_SETTINGS, language: "en" });
    expect(loadSettings(memoryStorage(stored), ["ru-RU"]).language).toBe("en");
  });

  it("survives corrupted storage", () => {
    expect(loadSettings(memoryStorage("{{{"), ["en"])).toEqual(
      { ...DEFAULT_SETTINGS, language: "en" },
    );
  });

  it("fills in fields a newer version added", () => {
    const partial = JSON.stringify({ sensitivity: 2 });
    const loaded = loadSettings(memoryStorage(partial), ["en"]);
    expect(loaded.sensitivity).toBe(2);
    expect(loaded.haptics).toBe(DEFAULT_SETTINGS.haptics);
  });

  it("refuses an out-of-range sensitivity", () => {
    const absurd = JSON.stringify({ sensitivity: 9999 });
    expect(loadSettings(memoryStorage(absurd), ["en"]).sensitivity)
      .toBe(DEFAULT_SETTINGS.sensitivity);
  });

  it("survives storage that throws", () => {
    const hostile = {
      getItem: () => {
        throw new Error("private mode");
      },
    } as unknown as Storage;
    expect(loadSettings(hostile, ["en"]).language).toBe("en");
  });
});

describe("saveSettings", () => {
  it("round-trips", () => {
    const storage = memoryStorage();
    const settings: Settings = { ...DEFAULT_SETTINGS, sensitivity: 1.8, language: "ru" };
    saveSettings(storage, settings);
    expect(loadSettings(storage, ["en"])).toEqual(settings);
  });

  it("does not throw when storage refuses to write", () => {
    const hostile = {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota");
      },
    } as unknown as Storage;
    expect(() => saveSettings(hostile, DEFAULT_SETTINGS)).not.toThrow();
  });
});
