import { useEffect, useRef } from "react";

interface Props {
  onFire: () => void;
  repeat?: boolean;
  className?: string;
  label: string;
  children: React.ReactNode;
}

const REPEAT_MS = 110;

/** A button that keeps firing while held, for arrows and volume steps. */
export function HoldButton({ onFire, repeat, className, label, children }: Props) {
  const timer = useRef<number | null>(null);

  useEffect(() => () => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
    }
  }, []);

  const start = (event: React.PointerEvent<HTMLButtonElement>): void => {
    event.preventDefault();
    onFire();
    if (repeat) {
      timer.current = window.setInterval(onFire, REPEAT_MS);
    }
  };

  const stop = (): void => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  };

  return (
    <button
      type="button"
      className={className}
      aria-label={label}
      onPointerDown={start}
      onPointerUp={stop}
      onPointerCancel={stop}
      onPointerLeave={stop}
    >
      {children}
    </button>
  );
}
