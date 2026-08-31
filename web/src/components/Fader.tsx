import { useEffect, useRef, useState } from "react";

import { FaderLock, SEND_INTERVAL_MS, valueFromPosition } from "../fader";

interface Props {
  value: number | null;
  min: number;
  max: number;
  disabled?: boolean;
  label: string;
  onChange: (value: number) => void;
  format?: (value: number) => string;
}

/**
 * A draggable fader.
 *
 * Used for both volume and track position; the only difference is the
 * range and what the caller does with the value.
 */
export function Fader({ value, min, max, disabled, label, onChange, format }: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const lockRef = useRef(new FaderLock());
  const lastSentAt = useRef(0);
  const [local, setLocal] = useState<number | null>(value);

  useEffect(() => {
    if (lockRef.current.accepts(performance.now())) {
      setLocal(value);
    }
  }, [value]);

  const apply = (clientX: number, force: boolean): void => {
    const track = trackRef.current;
    if (!track) {
      return;
    }
    const next = valueFromPosition(clientX, track.getBoundingClientRect(), min, max);
    setLocal(next);
    const now = performance.now();
    if (force || now - lastSentAt.current >= SEND_INTERVAL_MS) {
      lastSentAt.current = now;
      onChange(next);
    }
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (disabled) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    lockRef.current.grab();
    apply(event.clientX, true);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (disabled || !event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }
    apply(event.clientX, false);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>): void => {
    // Release first: if the fader was disabled mid-gesture, an early
    // return here would leave the lock held and the knob would never
    // accept incoming state again.
    const wasHeld = lockRef.current.accepts(performance.now()) === false;
    lockRef.current.release(performance.now());
    if (disabled || !wasHeld) {
      return;
    }
    apply(event.clientX, true);
  };

  const shown = local ?? min;
  const share = max > min ? ((shown - min) / (max - min)) * 100 : 0;

  return (
    <div
      className={`fader${disabled ? " disabled" : ""}`}
      role="slider"
      aria-label={label}
      aria-valuenow={Math.round(shown)}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div className="fader-track" ref={trackRef}>
        <div className="fader-fill" style={{ width: `${share}%` }} />
        <div className="fader-knob" style={{ left: `${share}%` }} />
      </div>
      {format ? <span className="fader-value">{format(shown)}</span> : null}
    </div>
  );
}
