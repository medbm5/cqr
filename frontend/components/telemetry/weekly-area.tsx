"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { SERIES, SURFACE_GAP } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import type { WeeklyBucket } from "@/lib/api";
import { compactNumber, fullNumber } from "@/lib/format";

const SERIES_ORDER = [
  { key: "siem_only", label: "SIEM only", color: SERIES.siem },
  { key: "both", label: "Both feeds", color: SERIES.both },
  { key: "edr_only", label: "EDR only", color: SERIES.edr },
] as const;

function shortWeek(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

function labelFor(key: unknown): string {
  return SERIES_ORDER.find((series) => series.key === key)?.label ?? String(key);
}

/**
 * Weekly event volume, split by which feed saw it.
 *
 * Three series a reader must tell apart, so this is the one categorical use on
 * the page. The middle band is the overlap deduplication exists for, and it is
 * plotted between the two feeds so its thickness reads directly as how much the
 * two agree.
 *
 * Stacked, because the three bands partition one total: the top edge is the
 * week's distinct event count and never double-counts.
 */
export function WeeklyArea({ weekly }: { weekly: WeeklyBucket[] }) {
  return (
    <ChartFrame
      title="Events per week, by which feed saw them"
      term="dedup"
      hint="Stacked: the top edge is the week's distinct event count"
      legend={SERIES_ORDER.map((entry) => ({ label: entry.label, color: entry.color }))}
      columns={[
        { key: "week", label: "Week of" },
        { key: "siem_only", label: "SIEM only", numeric: true },
        { key: "both", label: "Both", numeric: true },
        { key: "edr_only", label: "EDR only", numeric: true },
        { key: "merged", label: "Distinct", numeric: true },
      ]}
      rows={weekly.map((week) => ({
        week: shortWeek(week.week_start),
        siem_only: fullNumber(week.siem_only),
        both: fullNumber(week.both),
        edr_only: fullNumber(week.edr_only),
        merged: fullNumber(week.merged),
      }))}
    >
      {/* The height includes the x-axis band, so the axis is never cropped into
          a nested scrollbar. */}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={weekly} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#1B2942" strokeWidth={1} vertical={false} />
            <XAxis {...AXIS_PROPS} dataKey="week_start" tickFormatter={shortWeek} minTickGap={28} />
            <YAxis {...AXIS_PROPS} width={48} tickFormatter={compactNumber} />
            <Tooltip
              cursor={{ stroke: "#7A8AA0", strokeWidth: 1 }}
              content={({ active, payload, label }) =>
                active && payload && payload.length > 0 ? (
                  <TooltipShell title={`Week of ${shortWeek(String(label))}`}>
                    {[...payload].reverse().map((entry) => (
                      <TooltipRow
                        key={String(entry.dataKey)}
                        color={String(entry.color)}
                        label={labelFor(entry.dataKey)}
                        value={fullNumber(Number(entry.value))}
                      />
                    ))}
                  </TooltipShell>
                ) : null
              }
            />
            {SERIES_ORDER.map((entry) => (
              <Area
                key={entry.key}
                type="monotone"
                dataKey={entry.key}
                stackId="events"
                stroke={entry.color}
                strokeWidth={2}
                fill={entry.color}
                fillOpacity={0.18}
                activeDot={{ r: 4, stroke: SURFACE_GAP, strokeWidth: 2 }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  );
}
