"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { CHROME, SERIES } from "@/components/charts/tokens";
import { TooltipShell } from "@/components/charts/tooltip";
import type { ExceedanceCurve, SimulationResponse } from "@/lib/api";
import { compactEur, fullEur, percent } from "@/lib/format";

import { buildExceedanceSeries, decadeTicks, returnPeriodLabel } from "./exceedance-series";

const X_TICKS = [2, 5, 10, 20, 50, 100, 500, 1000, 10000];

/**
 * How bad a year gets, and how often.
 *
 * Both series are losses in euros, so they share **one** y-axis — two scales on
 * one plot would invent a relationship the data does not contain. Both axes are
 * logarithmic: return period spans 2 to 10,000 years and loss spans four orders
 * of magnitude, and on linear axes the whole curve collapses into a corner.
 *
 * AEP is the year's *total*; OEP is its *largest single* loss. OEP can never sit
 * above AEP at the same probability — the biggest loss of a year is at most that
 * year's total — and seeing the gap between them is the point of plotting both:
 * it is the difference between a capital question and a per-incident limit.
 *
 * **The left edge is empty on purpose.** Most years hold no incident, so the
 * loss exceeded with probability 0.5 is zero, and zero has no place on a log
 * axis. Those points are dropped from the lines and the band they occupied is
 * shaded and labelled instead — the absence is a finding, so it is stated rather
 * than trimmed away.
 */
export function ExceedanceCurves({
  aep,
  oep,
  metrics,
}: {
  aep: ExceedanceCurve;
  oep: ExceedanceCurve;
  metrics: SimulationResponse["metrics"];
}) {
  const { points, firstPlottedPeriod, zeroRegionEnd, xDomain, yDomain } = buildExceedanceSeries(
    aep,
    oep,
  );

  if (firstPlottedPeriod === null) {
    return (
      <ChartFrame
        title="Exceedance curves"
        hint="No simulated year carried a loss, so there is no curve to draw"
        columns={[{ key: "period", label: "Return period" }]}
        rows={[]}
      >
        <p className="py-8 text-center text-sm text-ink-muted">
          Every simulated year cost €0. An exceedance curve needs at least one loss-carrying
          year to have a shape.
        </p>
      </ChartFrame>
    );
  }

  // The two figures the tiles above report, placed on the curve they were read
  // off. They are exact quantiles, while the curve is evaluated on a log-spaced
  // probability grid that does not land precisely on 1-in-20 or 1-in-100 — so
  // the dots sit *on* the line rather than being read off it, and any visible
  // daylight between dot and line is grid resolution, not disagreement.
  const varMarkers = [
    { key: "var95", period: 20, value: metrics.var_95, label: "VaR 95" },
    { key: "var99", period: 100, value: metrics.var_99, label: "VaR 99" },
  ].filter(
    (marker) =>
      marker.value >= yDomain[0] &&
      marker.value <= yDomain[1] &&
      marker.period >= xDomain[0] &&
      marker.period <= xDomain[1],
  );

  return (
    <ChartFrame
      title="Exceedance curves"
      hint="Both axes logarithmic; both series are losses in euros on one scale"
      legend={[
        { label: "AEP — the year's total", color: SERIES.siem, shape: "line" },
        { label: "OEP — largest single loss", color: SERIES.edr, shape: "line" },
      ]}
      columns={[
        { key: "period", label: "Return period" },
        { key: "aep", label: "Annual total exceeds", numeric: true },
        { key: "oep", label: "Largest loss exceeds", numeric: true },
      ]}
      // The table keeps the zero rows the chart cannot draw: they are real
      // readings of the model, and the table is the complete twin of the chart
      // rather than a transcription of what happened to fit on the axes.
      rows={points.map((point) => ({
        period: returnPeriodLabel(point.period),
        aep: point.aep === null ? "€0" : fullEur(point.aep),
        oep: point.oep === null ? "€0" : fullEur(point.oep),
      }))}
    >
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={CHROME.grid} strokeWidth={1} />
            <XAxis
              {...AXIS_PROPS}
              dataKey="period"
              type="number"
              scale="log"
              domain={xDomain}
              ticks={X_TICKS.filter((tick) => tick >= xDomain[0] && tick <= xDomain[1])}
              tickFormatter={(value: number) =>
                value >= 1000 ? `${value / 1000}k` : String(value)
              }
            />
            <YAxis
              {...AXIS_PROPS}
              width={56}
              scale="log"
              // An explicit domain, never "auto": on a log scale recharts
              // resolves "auto" through the data's minimum, and a zero there
              // produces a NaN axis that renders nothing at all.
              domain={yDomain}
              ticks={decadeTicks(yDomain)}
              tickFormatter={(value: number) => compactEur(value)}
            />

            {/* The band where the model says a year costs nothing. Drawn behind
                the lines, before them in source order. */}
            {zeroRegionEnd !== null ? (
              <ReferenceArea
                x1={xDomain[0]}
                x2={firstPlottedPeriod}
                fill={CHROME.grid}
                fillOpacity={0.55}
                stroke="none"
                label={{
                  value: "expected year costs €0",
                  fill: CHROME.inkMuted,
                  fontSize: 10,
                  position: "insideTopLeft",
                }}
              />
            ) : null}

            <Tooltip
              cursor={{ stroke: CHROME.axis, strokeWidth: 1 }}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const period = Number(label);

                // Only series that actually have a value here. Left of a
                // curve's first point its entry is null, and a row reading
                // "exceeds €0" would be a fabricated reading, not a datum.
                const rows = [
                  { key: "aep", color: SERIES.siem, text: "the year's total exceeds" },
                  { key: "oep", color: SERIES.edr, text: "its largest single loss exceeds" },
                ]
                  .map((row) => ({
                    ...row,
                    value: payload.find((entry) => entry.dataKey === row.key)?.value,
                  }))
                  .filter(
                    (row): row is typeof row & { value: number } =>
                      typeof row.value === "number" && row.value > 0,
                  );

                if (rows.length === 0) {
                  return (
                    <TooltipShell title={`${returnPeriodLabel(period)} loss`}>
                      <li className="text-xs text-ink-secondary">
                        A year this ordinary costs nothing — most years hold no incident.
                      </li>
                    </TooltipShell>
                  );
                }

                return (
                  <TooltipShell title={`${returnPeriodLabel(period)} loss`}>
                    {rows.map((row) => (
                      <li key={row.key} className="flex items-baseline gap-2">
                        <span
                          aria-hidden
                          style={{ background: row.color }}
                          className="h-0.5 w-3 shrink-0 rounded-full"
                        />
                        <span className="text-xs text-ink-secondary">
                          {row.text}{" "}
                          <span className="tabular font-semibold text-ink">
                            {fullEur(row.value)}
                          </span>
                        </span>
                      </li>
                    ))}
                  </TooltipShell>
                );
              }}
            />

            <Line
              type="monotone"
              dataKey="aep"
              stroke={SERIES.siem}
              strokeWidth={2}
              dot={false}
              // Never bridge the gap: a connected null would draw a line
              // through return periods where the model reports no loss.
              connectNulls={false}
              activeDot={{ r: 4, stroke: CHROME.surface, strokeWidth: 2 }}
              animationDuration={700}
            />
            <Line
              type="monotone"
              dataKey="oep"
              stroke={SERIES.edr}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              activeDot={{ r: 4, stroke: CHROME.surface, strokeWidth: 2 }}
              animationDuration={700}
            />

            {varMarkers.map((marker) => (
              <ReferenceDot
                key={marker.key}
                x={marker.period}
                y={marker.value}
                r={4}
                fill={CHROME.ink}
                stroke={CHROME.surface}
                strokeWidth={2}
                label={{
                  value: `${marker.label} ${compactEur(marker.value)}`,
                  fill: CHROME.ink,
                  fontSize: 11,
                  position: "left",
                  offset: 10,
                }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-ink-muted">
        {`Read the x-axis as "once every N years". Below a ~${firstPlottedPeriod.toFixed(1)}-year ` +
          `return period the expected year costs €0 — ${percent(
            metrics.probability_of_no_loss,
          )} of years are loss-free, so there is nothing to plot on a log scale and that band ` +
          `is shaded instead. The two marked points are the VaR figures in the tiles above, ` +
          `placed on the curve they were read off.`}
      </p>
    </ChartFrame>
  );
}
