import { pickLanguage, type Language } from "./i18n";

export type Saturation = "calm" | "normal" | "rich";

export interface Settings {
  sensitivity: number;
  naturalScrolling: boolean;
  haptics: boolean;
  showMedia: boolean;
  saturation: Saturation;
  language: Language;
}

const KEY = "lanpad";
const MIN_SENSITIVITY = 0.5;
const MAX_SENSITIVITY = 2.4;

export const DEFAULT_SETTINGS: Settings = {
  sensitivity: 1.1,
  naturalScrolling: false,
  haptics: true,
  showMedia: true,
  saturation: "normal",
  language: "en",
};

function isSaturation(value: unknown): value is Saturation {
  return value === "calm" || value === "normal" || value === "rich";
}

/**
 * Read settings, falling back field by field.
 *
 * Storage can be absent, corrupted, or throw outright in private mode, and
 * a phone that cannot remember a preference should still work.
 */
export function loadSettings(storage: Storage, languages: readonly string[]): Settings {
  const fallback: Settings = { ...DEFAULT_SETTINGS, language: pickLanguage(languages) };
  let stored: unknown;
  try {
    const raw = storage.getItem(KEY);
    stored = raw === null ? null : JSON.parse(raw);
  } catch {
    return fallback;
  }
  if (typeof stored !== "object" || stored === null) {
    return fallback;
  }
  const partial = stored as Partial<Settings>;
  const sensitivity = typeof partial.sensitivity === "number"
    && partial.sensitivity >= MIN_SENSITIVITY
    && partial.sensitivity <= MAX_SENSITIVITY
    ? partial.sensitivity
    : fallback.sensitivity;
  return {
    sensitivity,
    naturalScrolling: typeof partial.naturalScrolling === "boolean"
      ? partial.naturalScrolling
      : fallback.naturalScrolling,
    haptics: typeof partial.haptics === "boolean" ? partial.haptics : fallback.haptics,
    showMedia: typeof partial.showMedia === "boolean" ? partial.showMedia : fallback.showMedia,
    saturation: isSaturation(partial.saturation) ? partial.saturation : fallback.saturation,
    language: partial.language === "ru" || partial.language === "en"
      ? partial.language
      : fallback.language,
  };
}

export function saveSettings(storage: Storage, settings: Settings): void {
  try {
    storage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // A phone that cannot remember preferences still works with them.
  }
}
