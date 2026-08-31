import { en, type Strings } from "./en";
import { ru } from "./ru";

export type Language = "en" | "ru";

const DICTIONARIES: Record<Language, Strings> = { en, ru };

/**
 * Pick a language from the phone's preference list.
 *
 * The first *understood* entry wins, not the first listed: a phone set to
 * German with Russian second should get Russian, not English.
 */
export function pickLanguage(preferred: readonly string[]): Language {
  for (const tag of preferred) {
    const base = tag.toLowerCase().split("-")[0];
    if (base === "ru") {
      return "ru";
    }
    if (base === "en") {
      return "en";
    }
  }
  return "en";
}

export function strings(language: Language): Strings {
  return DICTIONARIES[language];
}

export type { Strings };
