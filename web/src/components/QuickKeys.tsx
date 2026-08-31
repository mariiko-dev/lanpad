import type { Strings } from "../i18n";
import type { Event } from "../protocol";
import { HoldButton } from "./HoldButton";

interface Props {
  send: (event: Event) => void;
  strings: Strings;
  onKeyboard: () => void;
}

interface Key {
  label: string;
  tap?: string;
  combo?: string[];
  repeat?: boolean;
}

const KEYS: Key[] = [
  { label: "Esc", tap: "escape" },
  { label: "Tab", tap: "tab" },
  { label: "↵", tap: "enter" },
  { label: "⌫", tap: "backspace" },
  { label: "↑", tap: "up", repeat: true },
  { label: "↓", tap: "down", repeat: true },
  { label: "←", tap: "left", repeat: true },
  { label: "→", tap: "right", repeat: true },
  { label: "⌘", tap: "super" },
  { label: "Alt+Tab", combo: ["alt", "tab"] },
  { label: "Ctrl+C", combo: ["ctrl", "c"] },
  { label: "Ctrl+V", combo: ["ctrl", "v"] },
];

export function QuickKeys({ send, strings, onKeyboard }: Props) {
  return (
    <div className="keys">
      {KEYS.map((key) => (
        <HoldButton
          key={key.label}
          label={key.label}
          repeat={key.repeat}
          onFire={() => send(key.combo ? ["combo", key.combo] : ["tap", key.tap ?? ""])}
        >
          {key.label}
        </HoldButton>
      ))}
      <button type="button" className="kbkey" aria-label={strings.keyboard}
              onClick={onKeyboard}>⌨</button>
    </div>
  );
}
