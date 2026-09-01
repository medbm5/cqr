"use client";

import { motion, useReducedMotion, useScroll, useSpring } from "framer-motion";
import { useRef } from "react";

import { PHASES, ROADMAP, type RoadmapItem } from "@/lib/roadmap";

import { RoadmapCard, THEME_DOT } from "./roadmap-card";

/**
 * The roadmap as a timeline.
 *
 * A spine down the left with every card docked to it, grouped into three phases
 * under sticky headers. The single left rail is what carries the argument: these
 * are not seventeen independent ideas, they are one ordered sequence, and the
 * order is the claim.
 *
 * The spine draws itself against scroll progress rather than animating once on
 * mount. Progress through the page *is* progress through the plan, so tying the
 * two together costs nothing and means the reader can always see how much of the
 * roadmap is left.
 */
export function RoadmapTimeline() {
  const reduceMotion = useReducedMotion();
  const container = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: container,
    offset: ["start 0.85", "end 0.55"],
  });
  // Springing the raw progress stops the line jittering on a trackpad's
  // sub-pixel scroll events without letting it lag behind the cards.
  const drawn = useSpring(scrollYProgress, { stiffness: 120, damping: 30, restDelta: 0.001 });

  const byPhase = PHASES.map((meta) => ({
    meta,
    items: ROADMAP.filter((item) => item.phase === meta.phase),
  }));

  return (
    <div ref={container} className="relative pl-8">
      {/* The track, and the part of it the reader has travelled. Decorative: the
          phase headings below carry the same structure as text. */}
      <div aria-hidden className="absolute bottom-0 left-3 top-0 w-px bg-navy-800" />
      <motion.div
        aria-hidden
        style={{ scaleY: reduceMotion ? 1 : drawn }}
        className="absolute bottom-0 left-3 top-0 w-px origin-top bg-gradient-to-b from-accent via-accent/60 to-accent/10"
      />

      <div className="space-y-12">
        {byPhase.map(({ meta, items }) => (
          <section key={meta.phase} aria-labelledby={`phase-${meta.phase}`}>
            {/* Sticky from `lg` up only. Below that the nav is itself a sticky
                strip across the top, and a second sticky element would dock
                underneath it and never be seen. */}
            <header className="z-10 -mx-2 mb-5 bg-navy-950/90 px-2 py-3 backdrop-blur lg:sticky lg:top-0">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h2
                  id={`phase-${meta.phase}`}
                  className="text-sm font-semibold tracking-tight text-ink"
                >
                  Phase {meta.phase} — {meta.title}
                </h2>
                <span className="text-xs text-ink-muted">
                  {items.length} item{items.length === 1 ? "" : "s"}
                </span>
              </div>
              <p className="mt-1 max-w-2xl text-xs leading-relaxed text-ink-secondary">
                {meta.summary}
              </p>
            </header>

            <div className="space-y-4">
              {items.map((item, index) => (
                <RoadmapCard key={item.id} item={item} index={index} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

/**
 * What the chips and badges mean, stated once.
 *
 * A legend rather than a tooltip on each card: three themes and three effort
 * sizes are few enough to learn in one pass, and repeating the definition
 * seventeen times would be noise.
 */
export function RoadmapLegend() {
  const themes: { theme: RoadmapItem["theme"]; label: string }[] = [
    { theme: "modeling", label: "modeling — changes the number" },
    { theme: "platform", label: "platform — changes the product" },
    { theme: "data", label: "data — changes what feeds it" },
  ];

  return (
    <div className="mb-8 flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border border-navy-800 bg-navy-900 px-5 py-4">
      <ul className="flex flex-wrap gap-x-5 gap-y-2">
        {themes.map(({ theme, label }) => (
          <li key={theme} className="flex items-center gap-2 text-xs text-ink-secondary">
            <span
              aria-hidden
              style={{ background: THEME_DOT[theme] }}
              className="h-2 w-2 shrink-0 rounded-full"
            />
            {label}
          </li>
        ))}
      </ul>
      <p className="text-xs text-ink-muted">
        <span className="font-semibold text-ink-secondary">S · M · L</span> — days, weeks,
        months
      </p>
    </div>
  );
}
