"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { ChartFrame } from "@/components/charts/chart-frame";
import { SEVERITY_COLORS, SURFACE_GAP } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import { compactNumber, fullNumber, percent } from "@/lib/format";

const ORDER = ["critical", "high", "medium", "low", "unknown"] as const;

const TITLES: Record<string, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  unknown: "Ungraded",
};

/**
 * The severity mix of every distinct event.
 *
 * Severity is an *ordered* scale, so the fill is the ordinal ramp rather than
 * five unrelated hues — the reader sees the order in the colour as well as the
 * label. `unknown` sits deliberately off that ramp in a neutral: an ungraded
 * event is unknown, not mild, and giving it the lightest step would assert
 * something the data does not say.
 *
 * A donut compares close values badly, and two of these are within 3% of each
 * other, so every segment is direct-labelled with its count and share. Nobody
 * has to judge one arc against another.
 */
export function SeverityDonut({ mix }: { mix: Record<string, number> }) {
  const total = Object.values(mix).reduce((sum, value) => sum + value, 0);
  const data = ORDER.filter((key) => (mix[key] ?? 0) > 0).map((key) => ({
    key,
    label: TITLES[key] ?? key,
    value: mix[key] ?? 0,
    color: SEVERITY_COLORS[key] ?? SEVERITY_COLORS.unknown,
  }));

  return (
    <ChartFrame
      title="Severity mix"
      hint={`${fullNumber(total)} distinct events; the worst grade wins where feeds disagree`}
      legend={data.map((entry) => ({ label: entry.label, color: String(entry.color) }))}
      columns={[
        { key: "label", label: "Severity" },
        { key: "value", label: "Events", numeric: true },
        { key: "share", label: "Share", numeric: true },
      ]}
      rows={data.map((entry) => ({
        label: entry.label,
        value: fullNumber(entry.value),
        share: percent(entry.value / total),
      }))}
    >
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <div className="relative h-52 w-52 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                innerRadius="62%"
                outerRadius="98%"
                startAngle={90}
                endAngle={-270}
                paddingAngle={1.5}
                stroke={SURFACE_GAP}
                strokeWidth={2}
                animationDuration={600}
              >
                {data.map((entry) => (
                  <Cell key={entry.key} fill={String(entry.color)} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  const slice = payload?.[0];
                  if (!active || !slice) return null;
                  const datum = slice.payload as { label: string; color: string };
                  return (
                    <TooltipShell title="Severity">
                      <TooltipRow
                        color={datum.color}
                        label={datum.label}
                        value={fullNumber(Number(slice.value))}
                      />
                    </TooltipShell>
                  );
                }}
              />
            </PieChart>
          </ResponsiveContainer>

          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-semibold tracking-tight text-ink">
              {compactNumber(total)}
            </span>
            <span className="text-xs text-ink-muted">events</span>
          </div>
        </div>

        {/* Direct labels carry the values a donut cannot be read for. */}
        <dl className="min-w-0 flex-1 space-y-2">
          {data.map((entry) => (
            <div key={entry.key} className="flex items-center gap-3">
              <span
                aria-hidden
                style={{ background: String(entry.color) }}
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
              />
              <dt className="min-w-0 flex-1 truncate text-xs text-ink-secondary">{entry.label}</dt>
              <dd className="tabular text-xs font-semibold text-ink">{fullNumber(entry.value)}</dd>
              <dd className="tabular w-12 text-right text-xs text-ink-muted">
                {percent(entry.value / total, 0)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </ChartFrame>
  );
}
