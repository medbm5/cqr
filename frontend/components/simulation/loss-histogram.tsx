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
import { SERIES } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import { compactEur, compactNumber, fullEur, fullNumber } from "@/lib/format";

/**
 * Every simulated year, binned.
 *
 * One series, so one hue and no legend box. The two reference lines are the
 * figures the page leads with — where the mean sits against the median is the
 * whole shape of a loss distribution, and on this data they sit almost on top
 * of each other, which is itself the finding.
 */
export function LossHistogram({
  histogram,
  aal,
  median,
  years,
}: {
  histogram: { bin_edges_eur: number[]; counts: number[] };
  aal: number;
  median: number;
  years: number;
}) {
  const data = histogram.counts.map((count, index) => {
    const left = histogram.bin_edges_eur[index] ?? 0;
    const right = histogram.bin_edges_eur[index + 1] ?? left;
    return { centre: (left + right) / 2, left, right, count };
  });

  return (
    <ChartFrame
      title="Simulated annual loss"
      hint={`${fullNumber(years)} independent years, binned`}
      columns={[
        { key: "range", label: "Annual loss between" },
        { key: "count", label: "Years", numeric: true },
        { key: "share", label: "Share", numeric: true },
      ]}
      rows={data.map((row) => ({
        range: `${compactEur(row.left)} – ${compactEur(row.right)}`,
        count: fullNumber(row.count),
        share: `${((row.count / years) * 100).toFixed(2)}%`,
      }))}
    >
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1B2942" strokeWidth={1} vertical={false} />
            <XAxis
              {...AXIS_PROPS}
              dataKey="centre"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(value: number) => compactEur(value)}
              minTickGap={40}
            />
            <YAxis {...AXIS_PROPS} width={48} tickFormatter={compactNumber} />
            <Tooltip
              cursor={{ fill: "#111C31" }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | { left: number; right: number; count: number }
                  | undefined;
                if (!active || !point) return null;
                return (
                  <TooltipShell
                    title={`${compactEur(point.left)} to ${compactEur(point.right)}`}
                  >
                    <TooltipRow
                      color={SERIES.siem}
                      label={`years of ${fullNumber(years)}`}
                      value={fullNumber(point.count)}
                    />
                  </TooltipShell>
                );
              }}
            />
            <ReferenceLine
              x={median}
              stroke="#7A8AA0"
              strokeWidth={1}
              label={{ value: "median", fill: "#7A8AA0", fontSize: 11, position: "top" }}
            />
            <ReferenceLine
              x={aal}
              stroke="#FBBF24"
              strokeWidth={1}
              label={{ value: "AAL", fill: "#FBBF24", fontSize: 11, position: "top" }}
            />
            <Bar dataKey="count" fill={SERIES.siem} maxBarSize={18} animationDuration={600} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-ink-muted">
        Mean {fullEur(aal)} against a median year of {fullEur(median)}.
      </p>
    </ChartFrame>
  );
}
