"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { SERIES } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import type { SeverityFit } from "@/lib/api";
import { compactEur, fullEur } from "@/lib/format";

/** Linear interpolation of the fitted density at an arbitrary log-loss. */
function interpolate(xs: number[], ys: number[], at: number): number {
  if (xs.length === 0) return 0;
  if (at <= xs[0]!) return ys[0] ?? 0;
  if (at >= xs[xs.length - 1]!) return ys[ys.length - 1] ?? 0;
  for (let i = 1; i < xs.length; i += 1) {
    const left = xs[i - 1]!;
    const right = xs[i]!;
    if (at <= right) {
      const span = right - left || 1;
      const t = (at - left) / span;
      return (ys[i - 1] ?? 0) * (1 - t) + (ys[i] ?? 0) * t;
    }
  }
  return ys[ys.length - 1] ?? 0;
}

/**
 * The weighted peer losses this fit was made on, against the fit itself.
 *
 * Plotted on the log scale, because that is the only scale a six-order-of-
 * magnitude loss distribution is legible on: on a linear axis 99% of the mass
 * sits in the first pixel. The bars are the *peer-weighted* distribution, not
 * the raw incident base — the bar heights already carry the soft weighting, so
 * what the reader compares the curve against is what the fit actually saw.
 *
 * Two series, so a legend is present. The curve is the model's claim; the bars
 * are the evidence. Where they part company is the whole diagnostic.
 */
export function FitHistogram({ fit }: { fit: SeverityFit }) {
  const { plot } = fit.diagnostics;
  const data = plot.bin_density.map((density, index) => {
    const left = plot.bin_edges_log[index] ?? 0;
    const right = plot.bin_edges_log[index + 1] ?? left;
    const centre = (left + right) / 2;
    return {
      centre,
      eur: Math.exp(centre),
      observed: density,
      fitted: interpolate(plot.curve_x_log, plot.curve_y, centre),
    };
  });

  return (
    <ChartFrame
      title="Peer losses against the fitted distribution"
      term="lognormal"
      hint="Log scale; bar heights carry the peer weighting the fit was made on"
      legend={[
        { label: "Weighted peer losses", color: SERIES.siem },
        { label: "Fitted lognormal", color: SERIES.edr, shape: "line" },
      ]}
      columns={[
        { key: "eur", label: "Loss around", numeric: true },
        { key: "observed", label: "Observed density", numeric: true },
        { key: "fitted", label: "Fitted density", numeric: true },
      ]}
      rows={data.map((row) => ({
        eur: fullEur(row.eur),
        observed: row.observed.toFixed(4),
        fitted: row.fitted.toFixed(4),
      }))}
    >
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1B2942" strokeWidth={1} vertical={false} />
            <XAxis
              {...AXIS_PROPS}
              dataKey="eur"
              type="number"
              scale="log"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(value: number) => compactEur(value)}
              minTickGap={36}
            />
            <YAxis
              {...AXIS_PROPS}
              width={44}
              tickFormatter={(value: number) => value.toFixed(2)}
              label={undefined}
            />
            <Tooltip
              cursor={{ fill: "#111C31" }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | { eur: number; observed: number; fitted: number }
                  | undefined;
                if (!active || !point) return null;
                return (
                  <TooltipShell title={`Losses around ${fullEur(point.eur)}`}>
                    <TooltipRow
                      color={SERIES.siem}
                      label="observed density"
                      value={point.observed.toFixed(3)}
                    />
                    <TooltipRow
                      color={SERIES.edr}
                      label="fitted density"
                      value={point.fitted.toFixed(3)}
                    />
                  </TooltipShell>
                );
              }}
            />
            <Bar dataKey="observed" fill={SERIES.siem} fillOpacity={0.75} maxBarSize={20} />
            <Line
              type="monotone"
              dataKey="fitted"
              stroke={SERIES.edr}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: "#0A1120", strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  );
}
