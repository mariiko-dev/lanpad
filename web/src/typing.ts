import { canTypeDirectly } from "./keymap";

/**
 * How a batched run of typed text should reach the agent.
 *
 * A buffer the agent's layout covers end to end is typed key by key
 * (`type`); anything with Cyrillic, emoji or other non-ASCII travels
 * once through the clipboard (`paste`).
 */
export function flushMethod(buffer: string): "type" | "paste" {
  return canTypeDirectly(buffer) ? "type" : "paste";
}
