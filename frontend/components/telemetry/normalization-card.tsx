import { Card, CardHeader } from "@/components/ui/card";
import type { NormalizationReport } from "@/lib/api";
import { fullNumber, percent } from "@/lib/format";

function day(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/**
 * The accounting behind every number downstream.
 *
 * Deliberately a table of figures rather than a chart: these are six unrelated
 * quantities, not a distribution, and a reader checking whether the rows add up
 * wants to read them, not measure them.
 */
export function NormalizationCard({ report }: { report: NormalizationReport }) {
  const rows = [
    {
      label: "Raw rows read",
      value: fullNumber(report.rows_read),
      note: report.feeds
        .map((feed) => `${feed.source.toUpperCase()} ${fullNumber(feed.rows_read)}`)
        .join(" · "),
    },
    {
      label: "Duplicate reports merged",
      value: fullNumber(report.duplicates_merged),
      note: `${fullNumber(report.events_in_both_feeds)} of them seen by both feeds`,
    },
    {
      label: "Distinct events",
      value: fullNumber(report.total_events),
      note: `Concatenating instead would overstate by ${percent(report.inflation_avoided)}`,
    },
    {
      label: "Observation window",
      value: `${report.window.observed_days} days`,
      note: `${day(report.window.start)} to ${day(report.window.end)}`,
    },
    {
      label: "Annualization factor",
      value: report.window.annualization_factor.toFixed(6),
      note: `365 / ${report.window.observed_days}, recomputed from the data`,
    },
    {
      label: "Unknown assets",
      value: fullNumber(report.unknown_asset_ids.length),
      note:
        report.unknown_asset_ids.length === 0
          ? "Every asset id resolves against the reference"
          : report.unknown_asset_ids.slice(0, 5).join(", "),
    },
  ];

  return (
    <Card>
      <CardHeader title="Normalization report" hint="Every row accounted for" />
      <dl className="divide-y divide-navy-800">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-4 px-5 py-3">
            <div className="min-w-0">
              <dt className="text-xs font-medium text-ink-secondary">{row.label}</dt>
              <dd className="mt-0.5 truncate text-xs text-ink-muted">{row.note}</dd>
            </div>
            <dd className="tabular shrink-0 text-sm font-semibold text-ink">{row.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
