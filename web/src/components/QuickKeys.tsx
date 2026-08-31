import { useState, type ReactNode } from "react";
import {
  LuChevronDown, LuChevronLeft, LuChevronRight, LuChevronUp,
  LuCornerDownLeft, LuDelete, LuKeyboard,
} from "react-icons/lu";

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
  icon?: ReactNode;
  tap?: string;
  combo?: string[];
  repeat?: boolean;
}

const ARROWS: Key[] = [
  { label: "↑", icon: <LuChevronUp />, tap: "up", repeat: true },
  { label: "↓", icon: <LuChevronDown />, tap: "down", repeat: true },
  { label: "←", icon: <LuChevronLeft />, tap: "left", repeat: true },
  { label: "→", icon: <LuChevronRight />, tap: "right", repeat: true },
];

const DRAWER_KEYS: Key[] = [
  { label: "Esc", tap: "escape" },
  { label: "Tab", tap: "tab" },
  { label: "↵", icon: <LuCornerDownLeft />, tap: "enter" },
  { label: "⌫", icon: <LuDelete />, tap: "backspace" },
];

const DRAWER_SHORTCUTS: Key[] = [
  { label: "⌘", tap: "super" },
  { label: "Alt+Tab", combo: ["alt", "tab"] },
  { label: "Ctrl+C", combo: ["ctrl", "c"] },
  { label: "Ctrl+V", combo: ["ctrl", "v"] },
];

export function QuickKeys({ send, strings, onKeyboard }: Props) {
  const [open, setOpen] = useState(false);

  const button = (key: Key): ReactNode => (
    <HoldButton
      key={key.label}
      label={key.label}
      repeat={key.repeat}
      onFire={() => send(key.combo ? ["combo", key.combo] : ["tap", key.tap ?? ""])}
    >
      {key.icon ?? key.label}
    </HoldButton>
  );

  return (
    <div className="quickkeys">
      {open ? (
        <div className="keys-drawer">
          <div className="keys-group">
            <span className="keys-group-label">{strings.keysGroup}</span>
            <div className="keys-group-row">{DRAWER_KEYS.map(button)}</div>
          </div>
          <div className="keys-group">
            <span className="keys-group-label">{strings.shortcutsGroup}</span>
            <div className="keys-group-row">{DRAWER_SHORTCUTS.map(button)}</div>
          </div>
        </div>
      ) : null}

      <div className="keys">
        {ARROWS.map(button)}
        <button type="button" className="kbkey" aria-label={strings.keyboard}
                onClick={onKeyboard}><LuKeyboard /></button>
        <button type="button" className="keys-more" aria-label={strings.moreKeys}
                aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          {open ? <LuChevronDown /> : <LuChevronUp />}
        </button>
      </div>
    </div>
  );
}
