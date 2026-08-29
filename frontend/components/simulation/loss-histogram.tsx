"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { CHROME, SERIES } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import type { SimulationResponse } from "@/lib/api";
import { compactEur, compactNumber, fullEur, fullNumber, percent } from "@/lib/format";

/** Decade ticks, in euros. Only those inside the plotted range are drawn. */
const DECADES = [1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9] as const;

/**
 * The figures marked on the distribution they were read off.
 *
 * All annotation, no series - so none of them wears a series hue, which on
 * every other chart in this app means "the SIEM feed" or "the EDR feed". The
 * AAL takes the caution accent because it is the headline; the rest are
 * neutral, and their labels are what tells them apart.
 */
const MARKERS = [
  { key: "aal", label: "AAL", dashed: false, color: "#FBBF24" },
  { key: "var95", label: "VaR 95", dashed: true, color: CHROME.axis },
  { key: "var99", label: "VaR 99", dashed: true, color: CHROME.axis },
  { key: "cap", label: "cap", dashed: false, color: CHROME.inkSecondary },
] as const;

/**
 * Every simulated year that cost something, binned on a log scale.
 *
 * Two things had to change for this chart to say anything at all.
 *
 * **Zero-loss years are not in it.** Roughly three years in four cost nothing,
 * so a bin holding them stands three orders of magnitude above every other bin
 * and presses the whole loss distribution flat against the axis. The chart then
 * shows one fact the reader already knows and hides the one it was drawn for.
 * That share is stated above the plot instead, at full size, where it reads as
 * the finding it is rather than as a bar nothing can be compared against.
 *
 * **The bins are log-spaced.** Annual losses here run from a few hundred euros
 * to tens of millions. Linear bins over that range put every loss-year in the
 * first two of forty. Log bins are equal-width on a log axis, so the bars stay
 * uniform and the shape - a broad mode around the typical incident, a long thin
 * tail - becomes legible.
 *
 * One series, so one hue and no legend box. The vertical rules are the figures
 * in the tiles above plus the plausibility cap, drawn on the distribution they
 * were read off: the AAL in the caution accent because it is the headline, the
 * two VaR levels as dashed hairlines, and the cap solid, because it is the one
 * line that is a constraint on the model rather than a reading of it.
 */
export function LossHistogram({
  histogram,
  metrics,
  cap,
  years,
}: {
  histogram: SimulationResponse["histogram"];
  metrics: SimulationResponse["metrics"];
  cap: SimulationResponse["loss_cap"];
  years: number;
}) {
  const { bin_edges_eur: edges, counts, zero_years: zeroYears, loss_years: lossYears } = histogram;

  const data = counts.map((count, index) => {
    const left = edges[index] ?? 0;
    const right = edges[index + 1] ?? left;
    return {
      // Geometric midpoint, not arithmetic: on a log axis the arithmetic centre
      // of a bin sits visibly right of the bin it belongs to.
      centre: Math.sqrt(left * right),
      left,
      right,
      count,
    };
  });

  const low = edges[0] ?? 1;
  const high = edges[edges.length - 1] ?? 1;
  const ticks = DECADES.filter((tick) => tick >= low && tick <= high);
  const zeroShare = years > 0 ? zeroYears / years : 0;
  const lossShare = years > 0 ? lossYears / years : 0;

  // The cap is marked because it is visible in the data whether or not it is
  // labelled: every year holding one capped incident lands in the same bin, so
  // the far right of the chart carries a spike. Unlabelled it reads as a bug;
  // labelled it reads as the modeling choice it is.
  const markers = [
    { ...MARKERS[0], value: metrics.aal },
    { ...MARKERS[1], value: metrics.var_95 },
    { ...MARKERS[2], value: metrics.var_99 },
    { ...MARKERS[3], value: cap.cap_eur },
  ].filter((marker) => marker.value >= low && marker.value <= high);

  return (
    <ChartFrame
      title="Simulated annual loss"
      term="monte_carlo"
      hintTerm="poisson"
      hint={`Loss years only (${percent(lossShare)} of ${fullNumber(
        years,
      )} years); zero years shown separately. Log-spaced bins.`}
      columns={[
        { key: "range", label: "Annual loss between" },
        { key: "count", label: "Years", numeric: true },
        { key: "share", label: "Share of all years", numeric: true },
      ]}
      // The table twin carries the zero years too. Dropping them here would
      // make the shares silently not sum, and the table is the accessible
      // reading of the chart, not a subset of it.
      rows={[
        {
          range: "€0 — no incident at all",
          count: fullNumber(zeroYears),
          share: percent(zeroShare, 2),
        },
        ...data.map((row) => ({
          range: `${compactEur(row.left)} – ${compactEur(row.right)}`,
          count: fullNumber(row.count),
          share: percent(years > 0 ? row.count / years : 0, 2),
        })),
      ]}
    >
      <ZeroYears count={zeroYears} share={zeroShare} years={years} />

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={CHROME.grid} strokeWidth={1} vertical={false} />
            <XAxis
              {...AXIS_PROPS}
              dataKey="centre"
              type="number"
              scale="log"
              domain={[low, high]}
              ticks={[...ticks]}
              tickFormatter={(value: number) => compactEur(value)}
            />
            <YAxis {...AXIS_PROPS} width={48} tickFormatter={compactNumber} />
            <Tooltip
              cursor={{ fill: CHROME.grid }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | { left: number; right: number; count: number }
                  | undefined;
                if (!active || !point) return null;
                return (
                  <TooltipShell title={`${compactEur(point.left)} to ${compactEur(point.right)}`}>
                    <TooltipRow
                      color={SERIES.siem}
                      label={`years of ${fullNumber(years)}`}
                      value={fullNumber(point.count)}
                    />
                  </TooltipShell>
                );
              }}
            />

            {markers.map((marker, index) => (
              <ReferenceLine
                key={marker.key}
                x={marker.value}
                stroke={marker.color}
                strokeWidth={1}
                strokeDasharray={marker.dashed ? "3 3" : undefined}
                label={{
                  value: marker.label,
                  fill: marker.color,
                  fontSize: 11,
                  position: "top",
                  // Staggered: on a log axis the AAL and VaR 95 can sit half a
                  // decade apart, which is close enough for two labels to
                  // overlap at this width.
                  offset: index % 2 === 0 ? 4 : 14,
                }}
              />
            ))}

            <Bar dataKey="count" fill={SERIES.siem} animationDuration={600} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-ink-muted">
        Across the {percent(lossShare)} of years that cost anything, the mean year is{" "}
        {fullEur(metrics.aal)} and the worst simulated year {fullEur(metrics.maximum)}. The
        median year is {fullEur(metrics.median)} because most years hold no incident at all.
        {cap.draws_capped > 0 ? (
          <>
            {" "}
            The bar at the cap is a pile-up, not a mode: every year holding one capped
            incident costs exactly {compactEur(cap.cap_eur)}, so they all land in one bin.
          </>
        ) : null}
      </p>
    </ChartFrame>
  );
}

/**
 * The years that cost nothing, stated rather than plotted.
 *
 * A proportional bar for 73% against bins holding fractions of a percent is not
 * a comparison a reader can make - it is one tall bar and forty flat ones. The
 * number is the whole point, so it is set as a number.
 */
function ZeroYears({ count, share, years }: { count: number; share: number; years: number }) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-lg border border-navy-700 bg-navy-950/60 px-4 py-3">
      <span className="tabular text-2xl font-semibold tracking-tight text-ink">
        {percent(share)}
      </span>
      <span className="text-sm text-ink-secondary">of years cost €0</span>
      <span className="tabular ml-auto text-xs text-ink-muted">
        {fullNumber(count)} of {fullNumber(years)} simulated years — no incident occurred
      </span>
    </div>
  );
}
