"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { SERIES } from "@/components/charts/tokens";
import { TooltipShell } from "@/components/charts/tooltip";
import type { ExceedanceCurve } from "@/lib/api";
import { compactEur, fullEur } from "@/lib/format";

function returnPeriod(years: number): string {
  if (years >= 1000) return `1-in-${Math.round(years / 1000)}k-year`;
  return `1-in-${Math.round(years)}-year`;
}

/**
 * How bad a year gets, and how often.
 *
 * Both series are losses in euros, so they share **one** y-axis — two scales on
 * one plot would invent a relationship the data does not contain. Both axes are
 * logarithmic: return period spans 2 to 10,000 years and loss spans an order of
 * magnitude, and on linear axes the whole curve collapses into a corner.
 *
 * AEP is the year's *total*; OEP is its *largest single* loss. OEP can never sit
 * above AEP at the same probability — the biggest loss of a year is at most that
 * year's total — and seeing the gap between them is the point of plotting both:
 * it is the difference between a capital question and a per-incident limit.
 */
export function ExceedanceCurves({ aep, oep }: { aep: ExceedanceCurve; oep: ExceedanceCurve }) {
  const data = aep.return_period_years.map((period, index) => ({
    period,
    aep: aep.loss_eur[index] ?? 0,
    oep: oep.loss_eur[index] ?? 0,
  }));

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
      rows={data.map((row) => ({
        period: returnPeriod(row.period),
        aep: fullEur(row.aep),
        oep: fullEur(row.oep),
      }))}
    >
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1B2942" strokeWidth={1} />
            <XAxis
              {...AXIS_PROPS}
              dataKey="period"
              type="number"
              scale="log"
              domain={["dataMin", "dataMax"]}
              ticks={[2, 5, 10, 20, 50, 100, 500, 1000, 10000]}
              tickFormatter={(value: number) => (value >= 1000 ? `${value / 1000}k` : String(value))}
            />
            <YAxis
              {...AXIS_PROPS}
              width={56}
              scale="log"
              domain={["auto", "auto"]}
              tickFormatter={(value: number) => compactEur(value)}
            />
            <Tooltip
              cursor={{ stroke: "#7A8AA0", strokeWidth: 1 }}
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const period = Number(label);
                const aepValue = payload.find((entry) => entry.dataKey === "aep")?.value;
                const oepValue = payload.find((entry) => entry.dataKey === "oep")?.value;
                return (
                  <TooltipShell title={`${returnPeriod(period)} loss`}>
                    <li className="flex items-baseline gap-2">
                      <span
                        aria-hidden
                        style={{ background: SERIES.siem }}
                        className="h-0.5 w-3 shrink-0 rounded-full"
                      />
                      <span className="text-xs text-ink-secondary">
                        the year&apos;s total exceeds{" "}
                        <span className="tabular font-semibold text-ink">
                          {fullEur(Number(aepValue))}
                        </span>
                      </span>
                    </li>
                    <li className="flex items-baseline gap-2">
                      <span
                        aria-hidden
                        style={{ background: SERIES.edr }}
                        className="h-0.5 w-3 shrink-0 rounded-full"
                      />
                      <span className="text-xs text-ink-secondary">
                        its largest single loss exceeds{" "}
                        <span className="tabular font-semibold text-ink">
                          {fullEur(Number(oepValue))}
                        </span>
                      </span>
                    </li>
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
              activeDot={{ r: 4, stroke: "#0A1120", strokeWidth: 2 }}
              animationDuration={700}
            />
            <Line
              type="monotone"
              dataKey="oep"
              stroke={SERIES.edr}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: "#0A1120", strokeWidth: 2 }}
              animationDuration={700}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-ink-muted">
        Read the x-axis as “once every N years”. Probabilities finer than the run can resolve
        are not plotted.
      </p>
    </ChartFrame>
  );
}
