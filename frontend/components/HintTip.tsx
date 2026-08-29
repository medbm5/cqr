"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";

import { GLOSSARY, type GlossaryKey } from "@/lib/glossary";

/** Distance from the viewport edge the tooltip refuses to cross, in pixels. */
const EDGE_MARGIN = 12;
const TOOLTIP_WIDTH = 280;

/**
 * An ⓘ that explains one mathematical concept in plain language.
 *
 * Opens on hover *and* on click, because a phone has no hover and a dashboard
 * full of statistics is exactly where a reader on a phone needs the help. A
 * click pins it open so the text can be read without keeping the pointer still.
 *
 * Copy never lives here — only in `lib/glossary.ts` — so the same concept reads
 * the same way wherever it appears.
 */
export function HintTip({ term, className = "" }: { term: GlossaryKey; className?: string }) {
  const entry = GLOSSARY[term];
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [offset, setOffset] = useState(0);
  const [below, setBelow] = useState(false);

  const wrapper = useRef<HTMLSpanElement>(null);
  const bubble = useRef<HTMLDivElement>(null);
  const tooltipId = useId();

  const close = useCallback(() => {
    setOpen(false);
    setPinned(false);
  }, []);

  // Escape closes, and outside clicks dismiss a pinned tooltip.
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        close();
        wrapper.current?.querySelector("button")?.focus();
      }
    };
    const onPointerDown = (event: PointerEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) close();
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open, close]);

  // Flip and shift so the bubble never leaves the viewport. Measured after
  // paint, because the answer depends on where the trigger actually landed.
  useLayoutEffect(() => {
    if (!open || !wrapper.current) return;

    const anchor = wrapper.current.getBoundingClientRect();
    const centre = anchor.left + anchor.width / 2;
    const half = TOOLTIP_WIDTH / 2;

    let shift = 0;
    if (centre - half < EDGE_MARGIN) shift = EDGE_MARGIN - (centre - half);
    else if (centre + half > window.innerWidth - EDGE_MARGIN) {
      shift = window.innerWidth - EDGE_MARGIN - (centre + half);
    }
    setOffset(shift);

    // Not enough room above? Open downward instead.
    const height = bubble.current?.offsetHeight ?? 120;
    setBelow(anchor.top - height - 12 < EDGE_MARGIN);
  }, [open]);

  return (
    <span ref={wrapper} className={`relative inline-flex align-middle ${className}`}>
      <button
        type="button"
        aria-label={`What is ${entry.term}?`}
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        onClick={() => {
          setPinned((wasPinned) => !wasPinned || !open);
          setOpen((wasOpen) => !(wasOpen && pinned));
        }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => {
          if (!pinned) setOpen(false);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          if (!pinned) setOpen(false);
        }}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full border border-navy-700 text-[9px] font-semibold leading-none text-ink-muted transition-colors duration-150 hover:border-accent/60 hover:text-accent"
      >
        i
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            ref={bubble}
            id={tooltipId}
            role="tooltip"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.15, ease: [0.16, 1, 0.3, 1] }}
            style={{
              width: TOOLTIP_WIDTH,
              left: "50%",
              transform: `translateX(calc(-50% + ${offset}px))`,
              transformOrigin: below ? "top center" : "bottom center",
              ...(below ? { top: "calc(100% + 8px)" } : { bottom: "calc(100% + 8px)" }),
            }}
            className="absolute z-50 rounded-lg border border-navy-700 bg-navy-850 p-3 text-left shadow-lift"
          >
            <p className="text-xs font-semibold text-ink">{entry.term}</p>
            <p className="mt-1 text-xs leading-relaxed text-ink-secondary">{entry.hint}</p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </span>
  );
}

/**
 * A label with its hint attached — the shape most call sites want.
 *
 * Saves repeating the flex wrapper everywhere and keeps the icon glued to the
 * end of the text rather than drifting to the end of the line.
 */
export function LabelWithHint({
  children,
  term,
  className = "",
}: {
  children: React.ReactNode;
  term: GlossaryKey;
  className?: string;
}) {
  return (
    <span className={`inline-flex items-center ${className}`}>
      {children}
      <HintTip term={term} />
    </span>
  );
}
