/** Browser key names the agent understands, by its own naming. */
const NAMED: Record<string, string> = {
  Escape: "escape",
  Tab: "tab",
  Enter: "enter",
  Backspace: "backspace",
  Delete: "delete",
  Home: "home",
  End: "end",
  PageUp: "pageup",
  PageDown: "pagedown",
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
};

export function namedKeyFor(key: string): string | null {
  return NAMED[key] ?? null;
}

/**
 * Can the agent type this key by key?
 *
 * Its layout covers printable ASCII. Anything else — Cyrillic, emoji —
 * travels through the clipboard instead.
 */
export function canTypeDirectly(text: string): boolean {
  return text.length > 0 && /^[\x20-\x7e]+$/.test(text);
}
