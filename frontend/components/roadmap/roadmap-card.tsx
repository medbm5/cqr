"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import type { RoadmapItem, RoadmapTheme } from "@/lib/roadmap";

/**
 * Theme colours.
 *
 * Colour is never the only channel here — every chip carries its theme as text
 * beside the swatch — so these are free to be chosen for separation on a dark
 * navy ground rather than constrained by a categorical-palette check.
 */
const THEME_CHIP: Record<RoadmapTheme, string> = {
  modeling: "border-accent/30 bg-accent-soft text-accent",
  platform: "border-[#A78BFA]/30 bg-[#A78BFA]/10 text-[#A78BFA]",
  data: "border-[#2DD4BF]/30 bg-[#2DD4BF]/10 text-[#2DD4BF]",
};

export const THEME_DOT: Record<RoadmapTheme, string> = {
  modeling: "#38BDF8",
  platform: "#A78BFA",
  data: "#2DD4BF",
};

/**
 * Collapsed height of the impact block: three lines of `text-xs leading-relaxed`.
 *
 * Expressed in `em` rather than measured, so the server and the first client
 * render agree exactly and the card never flashes open before collapsing.
 */
const COLLAPSED_HEIGHT = "4.875em";

const EFFORT_LABEL: Record<RoadmapItem["effort"], string> = {
  S: "Small — days",
  M: "Medium — weeks",
  L: "Large — months",
};

/**
 * One roadmap entry, docked to the timeline spine.
 *
 * The three sections are always in the same order and always carry the same
 * labels, because the value of a fixed structure is that a reader can compare
 * two items without reading either one twice. Today, the change, the
 * consequence — every card, no exceptions.
 *
 * Only the impact text expands. It is the section that runs long, because it is
 * where the honest version of "why this was not done" lives, and truncating it
 * everywhere would hide exactly the reasoning the page exists to show.
 */
export function RoadmapCard({ item, index }: { item: RoadmapItem; index: number }) {
  const reduceMotion = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [full, setFull] = useState<number | null>(null);
  const [collapsed, setCollapsed] = useState<number | null>(null);
  const impact = useRef<HTMLParagraphElement>(null);
  const window_ = useRef<HTMLDivElement>(null);

  // Height is animated between two measured pixel values rather than through a
  // `layout` animation. A layout animation on a block of text interpolates by
  // scaling it, which visibly squashes the glyphs for the length of the
  // transition; animating the containing window's height leaves the type alone.
  //
  // Measuring also decides whether the control appears at all: a "Read more" on
  // a paragraph that is already whole is a button that does nothing, and the
  // reader only finds that out by pressing it.
  useEffect(() => {
    const text = impact.current;
    const frame = window_.current;
    if (!text || !frame) return;

    const measure = () => {
      setFull(text.scrollHeight);
      setCollapsed(frame.clientHeight);
    };
    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(text);
    return () => observer.disconnect();
  }, []);

  // Before measurement lands, assume it fits: showing a control that might be
  // unnecessary is worse than adding one a moment later.
  const clipped = full !== null && collapsed !== null && full > collapsed + 1;

  return (
    <motion.article
      layout={reduceMotion ? false : "position"}
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{
        duration: 0.4,
        delay: reduceMotion ? 0 : Math.min(index, 4) * 0.06,
        ease: [0.16, 1, 0.3, 1],
      }}
      className="relative rounded-xl border border-navy-800 bg-navy-900 p-5 shadow-card transition duration-200 ease-out hover:-translate-y-0.5 hover:border-navy-700 hover:shadow-lift"
    >
      {/* The dot that pins this card to the spine. Hidden from assistive tech:
          the phase heading already says where in the sequence this sits. */}
      <span
        aria-hidden
        style={{ background: THEME_DOT[item.theme] }}
        className="absolute -left-[25px] top-7 h-2.5 w-2.5 rounded-full ring-4 ring-navy-950"
      />

      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <h3 className="text-sm font-semibold tracking-tight text-ink">{item.title}</h3>
        <div className="flex shrink-0 items-center gap-2">
          <span
            className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${THEME_CHIP[item.theme]}`}
          >
            {item.theme}
          </span>
          <span
            title={EFFORT_LABEL[item.effort]}
            className="rounded-full border border-navy-700 px-2 py-0.5 text-[10px] font-semibold text-ink-secondary"
          >
            <span className="sr-only">Effort: </span>
            {item.effort}
          </span>
        </div>
      </div>

      <dl className="mt-4 space-y-3 divide-y divide-navy-800">
        <Section label="Today" text={item.current} />
        <Section label="Change" text={item.change} className="pt-3" />

        <div className="pt-3">
          <dt className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
            Impact
          </dt>
          <dd>
            <motion.div
              ref={window_}
              // `initial={false}` makes framer-motion render the `animate`
              // height on the server too, so the collapsed box is correct in
              // the first painted frame rather than opening and snapping shut.
              className="mt-1 overflow-hidden"
              initial={false}
              animate={{ height: open ? (full ?? "auto") : COLLAPSED_HEIGHT }}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : { duration: 0.28, ease: [0.16, 1, 0.3, 1] }
              }
            >
              <p ref={impact} className="text-xs leading-relaxed text-ink-secondary">
                {item.impact}
              </p>
            </motion.div>
            {clipped || open ? (
              <button
                type="button"
                onClick={() => setOpen((value) => !value)}
                aria-expanded={open}
                className="mt-2 text-[11px] font-medium text-accent transition-colors hover:text-accent-strong"
              >
                {open ? "Show less" : "Read the reasoning"}
              </button>
            ) : null}
          </dd>
        </div>
      </dl>
    </motion.article>
  );
}

/** One labelled block of the fixed three-part structure. */
function Section({
  label,
  text,
  className = "",
}: {
  label: string;
  text: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">
        {label}
      </dt>
      <dd className="mt-1 text-xs leading-relaxed text-ink-secondary">{text}</dd>
    </div>
  );
}
