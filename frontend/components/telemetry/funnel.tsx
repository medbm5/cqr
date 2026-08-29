"use client";

import { motion, useReducedMotion } from "framer-motion";

import { HintTip } from "@/components/HintTip";
import { ChartFrame } from "@/components/charts/chart-frame";
import { ORDINAL_4, inkOn } from "@/components/charts/tokens";
import { fullNumber, percent } from "@/lib/format";
import type { GlossaryKey } from "@/lib/glossary";

export interface FunnelStage {
  label: string;
  value: number;
  note: string;
  /** The concept this stage introduces, explained on the label's ⓘ. */
  term?: GlossaryKey;
}

/**
 * The terminal stage: the rate the loss model actually consumes.
 *
 * Kept out of `FunnelStage` on purpose. It is not another count of the same
 * thing — the stages above are events, this is a *rate per year*, and it
 * arrives via a calibration rather than a filter. Giving it a proportional bar
 * would draw 0.31 against 45,840 and render it invisible, while implying the
 * two are the same measure. It gets its own row and the accent instead.
 */
export interface FunnelTerminal {
  label: string;
  value: number;
  note: string;
  term?: GlossaryKey;
}

/**
 * How raw feed rows become the incident rate the loss model prices.
 *
 * Ordered stages, so the fill is the **ordinal ramp** — one hue, monotone
 * lightness — and the reader sees the order in the colour as well as in the
 * length. The stages are not separate series, so there is no legend: the title
 * names the one measure.
 *
 * The SIEM/EDR split rides the first stage's caption rather than colouring it.
 * Splitting stage one into two feed hues would put a categorical colour job
 * (identity) inside an ordinal chart (position), and the reader would have to
 * hold two meanings for one channel.
 */
export function Funnel({
  stages,
  terminal,
}: {
  stages: FunnelStage[];
  terminal?: FunnelTerminal;
}) {
  const reduceMotion = useReducedMotion();
  const widest = Math.max(...stages.map((stage) => stage.value), 1);

  return (
    <ChartFrame
      title="From feed rows to loss incidents"
      hint="Each stage as a share of the raw rows both feeds delivered"
      columns={[
        { key: "stage", label: "Stage" },
        { key: "value", label: "Count", numeric: true },
        { key: "share", label: "Share of raw", numeric: true },
        { key: "note", label: "What happened" },
      ]}
      rows={[
        ...stages.map((stage) => ({
          stage: stage.label,
          value: fullNumber(stage.value),
          share: percent(stage.value / widest),
          note: stage.note,
        })),
        ...(terminal
          ? [
              {
                stage: terminal.label,
                value: terminal.value.toFixed(4),
                // A rate is not a share of the rows above it; saying so would be
                // a category error the table should not commit either.
                share: "—",
                note: terminal.note,
              },
            ]
          : []),
      ]}
    >
      <ol className="space-y-3">
        {stages.map((stage, index) => {
          const fraction = stage.value / widest;
          const fill = ORDINAL_4[ORDINAL_4.length - 1 - index] ?? ORDINAL_4[0];
          // Only label inside the bar when the text genuinely fits; otherwise it
          // sits outside the end. Never clipped.
          const labelInside = fraction > 0.28;

          return (
            <li key={stage.label}>
              <div className="flex items-baseline justify-between gap-4">
                <p className="text-xs font-medium text-ink-secondary">
                  {stage.label}
                  {stage.term ? <HintTip term={stage.term} /> : null}
                </p>
                <p className="text-xs text-ink-muted">{stage.note}</p>
              </div>

              <div className="mt-1.5 flex items-center gap-3">
                <div className="h-6 min-w-0 flex-1">
                  <motion.div
                    initial={reduceMotion ? false : { scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{
                      duration: 0.5,
                      delay: reduceMotion ? 0 : index * 0.12,
                      ease: [0.16, 1, 0.3, 1],
                    }}
                    style={{
                      width: `${Math.max(fraction * 100, 2)}%`,
                      background: fill,
                      transformOrigin: "left",
                    }}
                    className="flex h-6 items-center justify-end rounded-r pr-2"
                  >
                    {labelInside ? (
                      <span
                        style={{ color: inkOn(fill) }}
                        className="tabular text-xs font-semibold"
                      >
                        {fullNumber(stage.value)}
                      </span>
                    ) : null}
                  </motion.div>
                </div>
                {!labelInside ? (
                  <span className="tabular w-20 shrink-0 text-xs font-semibold text-ink">
                    {fullNumber(stage.value)}
                  </span>
                ) : (
                  <span className="tabular w-20 shrink-0 text-xs text-ink-muted">
                    {percent(fraction, 0)}
                  </span>
                )}
              </div>
            </li>
          );
        })}

        {terminal ? (
          <motion.li
            initial={reduceMotion ? false : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.35,
              // Last in the stagger, so the funnel visibly lands on it.
              delay: reduceMotion ? 0 : stages.length * 0.12,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="!mt-5 border-t border-navy-800 pt-4"
          >
            <div className="flex items-baseline justify-between gap-4">
              <p className="text-xs font-medium text-accent">
                {terminal.label}
                {terminal.term ? <HintTip term={terminal.term} /> : null}
              </p>
              <p className="text-xs text-ink-muted">{terminal.note}</p>
            </div>

            <div className="mt-1.5 flex items-center gap-3">
              {/* A badge, not a proportional bar: 0.31 against 45,840 would be
                  one invisible pixel, and the two are not the same measure. */}
              <span className="tabular inline-flex h-8 items-center rounded-lg border border-accent/40 bg-accent-soft px-3 text-base font-semibold text-accent">
                {terminal.value.toFixed(2)}
              </span>
              <span className="text-xs text-ink-secondary">
                loss-generating incidents per year — the rate the simulation draws from
              </span>
            </div>
          </motion.li>
        ) : null}
      </ol>
    </ChartFrame>
  );
}
