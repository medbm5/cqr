"use client";

import { motion } from "framer-motion";

import { FORMATTERS, type FormatKind } from "@/lib/format";

import { AnimatedCounter } from "./animated-counter";

/**
 * A signed change against a named baseline.
 *
 * `isGood` is separate from `direction` on purpose: down is good for duplicate
 * rows and bad for detection coverage, and a tile that colours by direction
 * alone gets one of those two wrong.
 */
export interface StatDelta {
  label: string;
  direction: "up" | "down";
  isGood: boolean;
  versus: string;
}

/**
 * One headline figure.
 *
 * Contract: a sentence-case label, a compacted value, and *either* a delta
 * against a named baseline or a caption giving the figure its context. Not
 * both — two subtitles under one number is two things to read and no hierarchy.
 */
export function StatTile({
  label,
  value,
  format,
  delta,
  caption,
  index = 0,
}: {
  label: string;
  value: number;
  format: FormatKind;
  delta?: StatDelta;
  caption?: string;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.05, ease: "easeOut" }}
      className="rounded-xl border border-navy-800 bg-navy-900 p-5 shadow-card transition duration-200 ease-out hover:-translate-y-0.5 hover:border-navy-700 hover:shadow-lift"
    >
      <p className="text-xs font-medium text-ink-secondary">{label}</p>

      {/* Proportional figures: tabular-nums makes a large standalone number
          look loose, and nothing here needs to align in a column. */}
      <AnimatedCounter
        value={value}
        format={FORMATTERS[format]}
        className="mt-3 block text-3xl font-semibold tracking-tight text-ink"
      />

      {delta ? (
        <p className="mt-2 flex items-baseline gap-1.5 text-xs">
          <span className={delta.isGood ? "text-positive" : "text-caution"}>
            <span aria-hidden>{delta.direction === "down" ? "▼" : "▲"}</span> {delta.label}
          </span>
          <span className="text-ink-muted">vs {delta.versus}</span>
        </p>
      ) : null}

      {!delta && caption ? <p className="mt-2 text-xs text-ink-muted">{caption}</p> : null}
    </motion.div>
  );
}
