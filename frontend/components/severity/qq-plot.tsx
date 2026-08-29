"use client";

import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { SERIES } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import type { SeverityFit } from "@/lib/api";
import { fullEur } from "@/lib/format";

/**
 * Quantiles the fit predicts, against the quantiles observed.
 *
 * The diagnostic that a KS statistic compresses into one number. A fit that
 * describes its data traces the diagonal; a tail the model misses bends the
 * upper right above it, and that bend is precisely where VaR and TVaR live.
 *
 * One series, so no legend — the title names what is plotted. The diagonal is a
 * *reference*, not data, so it is a neutral hairline rather than a second
 * series colour.
 */
export function QqPlot({ fit }: { fit: SeverityFit }) {
  const { qq_theoretical, qq_empirical } = fit.diagnostics;
  const data = qq_theoretical.map((theoretical, index) => ({
    theoretical,
    empirical: qq_empirical[index] ?? 0,
  }));

  const low = Math.min(...qq_theoretical, ...qq_empirical);
  const high = Math.max(...qq_theoretical, ...qq_empirical);
  const tail = fit.diagnostics.tail;

  return (
    <ChartFrame
      title="QQ plot of log-losses"
      hint={
        tail?.pareto_fits_tail_better
          ? `Weighted KS ${fit.diagnostics.weighted_ks.toFixed(3)} · a Pareto tail (α ${tail.alpha.toFixed(2)}) fits the extremes better`
          : `Weighted KS ${fit.diagnostics.weighted_ks.toFixed(3)}`
      }
      columns={[
        { key: "theoretical", label: "Fit predicts", numeric: true },
        { key: "empirical", label: "Observed", numeric: true },
      ]}
      rows={data.map((row) => ({
        theoretical: fullEur(Math.exp(row.theoretical)),
        empirical: fullEur(Math.exp(row.empirical)),
      }))}
    >
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1B2942" strokeWidth={1} />
            <XAxis
              {...AXIS_PROPS}
              type="number"
              dataKey="theoretical"
              domain={[low, high]}
              tickFormatter={(value: number) => `${(value / Math.LN10).toFixed(1)}`}
              name="fit predicts"
            />
            <YAxis
              {...AXIS_PROPS}
              type="number"
              dataKey="empirical"
              width={44}
              domain={[low, high]}
              tickFormatter={(value: number) => `${(value / Math.LN10).toFixed(1)}`}
              name="observed"
            />
            {/* The identity line: reference, not data, so it stays neutral. */}
            <ReferenceLine
              segment={[
                { x: low, y: low },
                { x: high, y: high },
              ]}
              stroke="#7A8AA0"
              strokeWidth={1}
            />
            <Tooltip
              cursor={{ stroke: "#7A8AA0", strokeWidth: 1 }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | { theoretical: number; empirical: number }
                  | undefined;
                if (!active || !point) return null;
                return (
                  <TooltipShell title="At this quantile">
                    <TooltipRow
                      color="#7A8AA0"
                      label="the fit predicts"
                      value={fullEur(Math.exp(point.theoretical))}
                    />
                    <TooltipRow
                      color={SERIES.siem}
                      label="peers actually lost"
                      value={fullEur(Math.exp(point.empirical))}
                    />
                  </TooltipShell>
                );
              }}
            />
            <Scatter
              data={data}
              fill={SERIES.siem}
              /* A 2px surface ring keeps overlapping points legible. */
              stroke="#0A1120"
              strokeWidth={2}
              shape="circle"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-ink-muted">
        Axes are log&#8321;&#8320; of the loss in euros. Points on the diagonal mean the fit and
        the peers agree.
      </p>
    </ChartFrame>
  );
}
