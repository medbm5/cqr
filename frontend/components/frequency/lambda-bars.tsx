"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { AXIS_PROPS, ChartFrame } from "@/components/charts/chart-frame";
import { SERIES } from "@/components/charts/tokens";
import { TooltipRow, TooltipShell } from "@/components/charts/tooltip";
import type { AttackType, FrequencyResponse } from "@/lib/api";
import { compactNumber, fullNumber } from "@/lib/format";

const LABELS: Record<AttackType, string> = {
  ransomware: "Ransomware",
  data_breach: "Data breach",
  credential_theft: "Credential theft",
  ddos: "DDoS",
  phishing: "Phishing",
  misconfiguration: "Misconfiguration",
  insider_error: "Insider error",
  supply_chain: "Supply chain",
  other: "Other",
};

/** Attack types the telemetry cannot see at all — a zero here is not an absence of risk. */
const UNOBSERVABLE: AttackType[] = ["supply_chain", "insider_error"];

/**
 * Annual attack rate per type.
 *
 * Attack types are *nominal* — swapping their order changes nothing — so every
 * bar takes the same single hue. Colouring them light-to-dark by value would
 * spend the identity channel re-encoding what bar length already shows, and
 * with one series there is no legend: the title names the measure.
 *
 * The two types the telemetry cannot observe are drawn at zero in a muted fill
 * and labelled, rather than dropped. A missing row reads as "not applicable";
 * a labelled zero reads as "we looked and could not see it", which is true.
 */
export function LambdaBars({
  frequency,
  dimmed = false,
}: {
  frequency: FrequencyResponse;
  dimmed?: boolean;
}) {
  const data = (Object.entries(frequency.lambda_detected_by_attack_type) as [AttackType, number][])
    .map(([attackType, rate]) => ({
      attackType,
      label: LABELS[attackType] ?? attackType,
      rate,
      episodes: frequency.episodes_by_attack_type[attackType] ?? 0,
      unobservable: UNOBSERVABLE.includes(attackType),
    }))
    .sort((a, b) => b.rate - a.rate);

  return (
    <ChartFrame
      title="Detected attacks per year, by type"
      term="lambda_detected"
      hintTerm="lambda_incident"
      hint={
        frequency.lambda_incident === null
          ? `${fullNumber(frequency.episodes)} episodes over ${frequency.observed_days} days, annualized`
          : `${fullNumber(frequency.episodes)} episodes over ${frequency.observed_days} days. These are detections — ${frequency.lambda_incident.toFixed(2)} of them per year become a loss.`
      }
      dimmed={dimmed}
      columns={[
        { key: "label", label: "Attack type" },
        { key: "episodes", label: "Episodes", numeric: true },
        { key: "rate", label: "Per year", numeric: true },
      ]}
      rows={data.map((row) => ({
        label: row.unobservable ? `${row.label} (not observable)` : row.label,
        episodes: fullNumber(row.episodes),
        rate: fullNumber(Math.round(row.rate)),
      }))}
    >
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 56, bottom: 0, left: 0 }}
            barCategoryGap="28%"
          >
            <CartesianGrid stroke="#1B2942" strokeWidth={1} horizontal={false} />
            <XAxis {...AXIS_PROPS} type="number" tickFormatter={compactNumber} />
            <YAxis
              {...AXIS_PROPS}
              type="category"
              dataKey="label"
              width={124}
              tick={{ fill: "#94A3B8", fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "#111C31" }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | { label: string; rate: number; episodes: number; unobservable: boolean }
                  | undefined;
                if (!active || !point) return null;
                return (
                  <TooltipShell title={point.label}>
                    <TooltipRow
                      color={SERIES.siem}
                      label="per year"
                      value={fullNumber(Math.round(point.rate))}
                    />
                    <TooltipRow
                      color="#4B5A72"
                      label="episodes observed"
                      value={fullNumber(point.episodes)}
                    />
                  </TooltipShell>
                );
              }}
            />
            <Bar
              dataKey="rate"
              radius={[0, 4, 4, 0]}
              maxBarSize={20}
              animationDuration={500}
              label={{
                position: "right",
                fill: "#94A3B8",
                fontSize: 11,
                formatter: (value: number) => (value > 0 ? compactNumber(value) : "not observable"),
              }}
            >
              {data.map((row) => (
                <Cell
                  key={row.attackType}
                  fill={row.unobservable ? "#26374F" : SERIES.siem}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  );
}
