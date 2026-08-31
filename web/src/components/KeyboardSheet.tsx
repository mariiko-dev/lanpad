import { useCallback, useEffect, useRef, useState } from "react";

import type { Strings } from "../i18n";
import { namedKeyFor } from "../keymap";
import type { Event } from "../protocol";
import { flushMethod } from "../typing";

interface Props {
  open: boolean;
  onClose: () => void;
  send: (event: Event) => void;
  strings: Strings;
}

type Modifier = "ctrl" | "alt" | "shift" | "super";

const MODIFIERS: Modifier[] = ["ctrl", "alt", "shift", "super"];
const MODIFIER_LABELS: Record<Modifier, string> = {
  ctrl: "Ctrl", alt: "Alt", shift: "Shift", super: "⌘",
};

// Typed characters are collected and sent as one event after a short
// idle, or once the run gets long. Sending each character on its own
// makes the agent run wl-copy + Ctrl+V per keystroke, which lags and
// clobbers the user's clipboard on every letter.
const FLUSH_IDLE_MS = 250;
const FLUSH_AT_LENGTH = 120;

/**
 * The keyboard sheet.
 *
 * Input is captured from a hidden field through `beforeinput` rather than
 * from key events: it is the only approach that reports characters
 * reliably on iOS, where key events for software keyboards are unusable.
 */
export function KeyboardSheet({ open, onClose, send, strings }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const [held, setHeld] = useState<Modifier[]>([]);
  const heldRef = useRef<Modifier[]>(held);
  heldRef.current = held;
  const [pasteText, setPasteText] = useState("");

  const bufferRef = useRef("");
  const timerRef = useRef<number | null>(null);

  const flush = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    const text = bufferRef.current;
    if (!text) {
      return;
    }
    bufferRef.current = "";
    send([flushMethod(text), text]);
  }, [send]);

  // Never leave a pending flush pointed at an unmounted component.
  useEffect(() => () => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
    }
  }, []);

  useEffect(() => {
    const field = inputRef.current;
    if (!field) {
      return undefined;
    }

    const pad = (): void => {
      if (field.value.length < 2) {
        field.value = "  ";
      }
      field.setSelectionRange(field.value.length, field.value.length);
    };

    const buffer = (text: string): void => {
      bufferRef.current += text;
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
      }
      if (bufferRef.current.length >= FLUSH_AT_LENGTH) {
        flush();
        return;
      }
      timerRef.current = window.setTimeout(flush, FLUSH_IDLE_MS);
    };

    const onBeforeInput = (event: InputEvent): void => {
      const { inputType, data } = event;
      if (inputType === "insertText" && data) {
        const modifiers = heldRef.current;
        if (modifiers.length > 0 && data.length === 1) {
          // A shortcut interrupts the run: send what is buffered first.
          flush();
          send(["combo", [...modifiers, data]]);
          setHeld([]);
        } else {
          buffer(data);
        }
      } else if (inputType === "insertLineBreak" || inputType === "insertParagraph") {
        flush();
        send(["tap", "enter"]);
      } else if (inputType === "deleteContentBackward") {
        flush();
        send(["tap", "backspace"]);
      } else if (inputType === "deleteWordBackward") {
        flush();
        send(["combo", ["ctrl", "backspace"]]);
      } else if (inputType === "insertFromPaste" && data) {
        flush();
        send(["paste", data]);
      }
      event.preventDefault();
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      const named = namedKeyFor(event.key);
      if (named) {
        flush();
        send(["tap", named]);
        event.preventDefault();
        return;
      }
      if (event.key.length === 1 && (event.ctrlKey || event.metaKey || event.altKey)) {
        const modifiers: string[] = [];
        if (event.ctrlKey) modifiers.push("ctrl");
        if (event.altKey) modifiers.push("alt");
        if (event.metaKey) modifiers.push("super");
        if (event.shiftKey) modifiers.push("shift");
        flush();
        send(["combo", [...modifiers, event.key.toLowerCase()]]);
        event.preventDefault();
      }
    };

    field.addEventListener("beforeinput", onBeforeInput as EventListener);
    field.addEventListener("keydown", onKeyDown);
    field.addEventListener("input", pad);
    return () => {
      field.removeEventListener("beforeinput", onBeforeInput as EventListener);
      field.removeEventListener("keydown", onKeyDown);
      field.removeEventListener("input", pad);
    };
  }, [send, flush]);

  useEffect(() => {
    const sheet = sheetRef.current;
    const field = inputRef.current;
    if (!sheet || !field) {
      return undefined;
    }
    if (!open) {
      flush();
      sheet.style.setProperty("--kb-h", "0px");
      setHeld([]);
      return undefined;
    }
    field.focus();
    const viewport = window.visualViewport;
    if (!viewport) {
      return undefined;
    }
    // Lift the sheet above the on-screen keyboard as it appears.
    const onResize = (): void => {
      const hidden = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
      sheet.style.setProperty("--kb-h", `${hidden}px`);
    };
    viewport.addEventListener("resize", onResize);
    viewport.addEventListener("scroll", onResize);
    onResize();
    return () => {
      viewport.removeEventListener("resize", onResize);
      viewport.removeEventListener("scroll", onResize);
    };
  }, [open, flush]);

  const toggle = (modifier: Modifier): void => {
    setHeld((current) => current.includes(modifier)
      ? current.filter((item) => item !== modifier)
      : [...current, modifier]);
    inputRef.current?.focus();
  };

  return (
    <div className={`kb${open ? " open" : ""}`} ref={sheetRef}>
      <div className="kb-mods">
        {MODIFIERS.map((modifier) => (
          <button key={modifier} type="button"
                  className={`kb-mod${held.includes(modifier) ? " on" : ""}`}
                  onPointerDown={(event) => { event.preventDefault(); toggle(modifier); }}>
            {MODIFIER_LABELS[modifier]}
          </button>
        ))}
      </div>
      <div className="kb-hint">{strings.keyboardHint}</div>
      <input ref={inputRef} className="kb-input" autoCapitalize="none"
             autoComplete="off" autoCorrect="off" spellCheck={false}
             aria-label={strings.keyboard} />
      <textarea className="kb-paste" value={pasteText} placeholder={strings.pasteField}
                onChange={(event) => setPasteText(event.target.value)} />
      <div className="kb-send">
        <button type="button" className="primary"
                onClick={() => pasteText && send(["paste", pasteText])}>{strings.paste}</button>
        <button type="button"
                onClick={() => pasteText && send(["tpaste", pasteText])}>{strings.pasteTerminal}</button>
      </div>
      <button type="button" className="kb-done" onClick={onClose}>{strings.done}</button>
    </div>
  );
}
