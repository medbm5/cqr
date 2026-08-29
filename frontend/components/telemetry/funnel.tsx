"use client";

import { motion, useReducedMotion } from "framer-motion";

import { ChartFrame } from "@/components/charts/chart-frame";
import { ORDINAL_4, inkOn } from "@/components/charts/tokens";
import { fullNumber, percent } from "@/lib/format";

export interface FunnelStage {
  label: string;
  value: number;
  note: string;
}

/**
 * How 45,840 rows become 5,325 attacks.
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
export function Funnel({ stages }: { stages: FunnelStage[] }) {
  const reduceMotion = useReducedMotion();
  const widest = Math.max(...stages.map((stage) => stage.value), 1);

  return (
    <ChartFrame
      title="From feed rows to attacks"
      hint="Each stage as a share of the raw rows both feeds delivered"
      columns={[
        { key: "stage", label: "Stage" },
        { key: "value", label: "Events", numeric: true },
        { key: "share", label: "Share of raw", numeric: true },
        { key: "note", label: "What happened" },
      ]}
      rows={stages.map((stage) => ({
        stage: stage.label,
        value: fullNumber(stage.value),
        share: percent(stage.value / widest),
        note: stage.note,
      }))}
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
                <p className="text-xs font-medium text-ink-secondary">{stage.label}</p>
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
      </ol>
    </ChartFrame>
  );
}
