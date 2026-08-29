"use client";

import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

/**
 * Counts a figure up on mount.
 *
 * The animation is a cue that the number was computed, not decoration — so it
 * is short, eases out, and never runs on a value the reader is re-reading. It
 * is skipped entirely under `prefers-reduced-motion`, where a settling number
 * is an obstacle rather than a flourish.
 */
export function AnimatedCounter({
  value,
  format,
  durationMs = 900,
  className = "",
}: {
  value: number;
  format: (value: number) => string;
  durationMs?: number;
  className?: string;
}) {
  const reduceMotion = useReducedMotion();
  const [shown, setShown] = useState(reduceMotion ? value : 0);
  const settled = useRef(false);

  useEffect(() => {
    if (reduceMotion || settled.current) {
      setShown(value);
      return;
    }
    settled.current = true;

    const controls = animate(0, value, {
      duration: durationMs / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => setShown(latest),
      onComplete: () => setShown(value),
    });
    return () => controls.stop();
  }, [value, durationMs, reduceMotion]);

  // The final value is in the DOM for assistive technology from the first
  // frame; only the visible text counts up.
  return (
    <span className={className}>
      <span aria-hidden>{format(shown)}</span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
