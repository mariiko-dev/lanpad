import { useEffect, useRef } from "react";

import { ScrollAccumulator, accelerate, isTap } from "../gestures";
import type { Event } from "../protocol";
import type { Settings } from "../settings";

interface Props {
  send: (event: Event) => void;
  settings: Settings;
  hint: string;
}

interface Point {
  x: number;
  y: number;
}

/**
 * The touch surface.
 *
 * Handlers are attached to the DOM node directly and never call setState:
 * a re-render per frame of finger movement is exactly the latency this
 * project exists to avoid.
 */
export function Trackpad({ send, settings, hint }: Props) {
  const padRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    const pad = padRef.current;
    const glow = glowRef.current;
    if (!pad || !glow) {
      return undefined;
    }

    const points = new Map<number, Point>();
    const scroll = new ScrollAccumulator();
    let startedAt = 0;
    let travelled = 0;
    let twoFinger = false;
    let dragArmed = false;
    let dragging = false;
    let lastTapAt = 0;

    const moveGlow = (x: number, y: number, visible: boolean): void => {
      const box = pad.getBoundingClientRect();
      glow.style.transform = `translate(${x - box.left}px, ${y - box.top}px)`;
      glow.style.opacity = visible ? "1" : "0";
    };

    const onStart = (event: TouchEvent): void => {
      event.preventDefault();
      for (const touch of Array.from(event.changedTouches)) {
        points.set(touch.identifier, { x: touch.clientX, y: touch.clientY });
      }
      const lead = event.changedTouches[0];
      if (lead) {
        moveGlow(lead.clientX, lead.clientY, true);
      }
      if (points.size === 1) {
        startedAt = performance.now();
        travelled = 0;
        twoFinger = false;
        dragArmed = performance.now() - lastTapAt < 300;
      }
    };

    const onMove = (event: TouchEvent): void => {
      event.preventDefault();
      const touches = Array.from(event.touches);
      const lead = touches[0];
      if (lead) {
        moveGlow(lead.clientX, lead.clientY, true);
      }

      if (points.size === 1 && touches.length === 1) {
        const touch = touches[0];
        const previous = points.get(touch.identifier);
        if (!previous) {
          return;
        }
        const dx = touch.clientX - previous.x;
        const dy = touch.clientY - previous.y;
        previous.x = touch.clientX;
        previous.y = touch.clientY;
        const distance = Math.hypot(dx, dy);
        travelled += distance;
        if (dragArmed && !dragging) {
          send(["bd", "l"]);
          dragging = true;
        }
        const factor = accelerate(distance, settingsRef.current.sensitivity);
        send(["m", Math.round(dx * factor), Math.round(dy * factor)]);
        return;
      }

      if (touches.length >= 2) {
        twoFinger = true;
        let sum = 0;
        let counted = 0;
        for (const touch of touches) {
          const previous = points.get(touch.identifier);
          if (previous) {
            sum += touch.clientY - previous.y;
            previous.x = touch.clientX;
            previous.y = touch.clientY;
            counted += 1;
          }
        }
        if (counted > 0) {
          travelled += Math.abs(sum);
          const notches = scroll.add(sum / counted, settingsRef.current.naturalScrolling);
          if (notches !== 0) {
            send(["w", notches]);
          }
        }
      }
    };

    const onEnd = (event: TouchEvent): void => {
      event.preventDefault();
      const last = event.changedTouches[0];
      for (const touch of Array.from(event.changedTouches)) {
        points.delete(touch.identifier);
      }
      if (points.size > 0) {
        return;
      }

      const elapsed = performance.now() - startedAt;
      if (dragging) {
        send(["bu", "l"]);
        dragging = false;
      } else if (twoFinger) {
        if (isTap(elapsed, travelled)) {
          send(["click", "r"]);
        }
      } else if (isTap(elapsed, travelled)) {
        send(["click", "l"]);
        lastTapAt = performance.now();
      }
      dragArmed = false;
      twoFinger = false;
      travelled = 0;
      if (last) {
        moveGlow(last.clientX, last.clientY, false);
      }
    };

    pad.addEventListener("touchstart", onStart, { passive: false });
    pad.addEventListener("touchmove", onMove, { passive: false });
    pad.addEventListener("touchend", onEnd, { passive: false });
    pad.addEventListener("touchcancel", onEnd, { passive: false });
    return () => {
      pad.removeEventListener("touchstart", onStart);
      pad.removeEventListener("touchmove", onMove);
      pad.removeEventListener("touchend", onEnd);
      pad.removeEventListener("touchcancel", onEnd);
    };
  }, [send]);

  return (
    <div className="pad" ref={padRef}>
      <div className="pad-glow" ref={glowRef} />
      <span className="pad-hint">{hint}</span>
    </div>
  );
}
