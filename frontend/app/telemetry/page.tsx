import { ApiUnavailable } from "@/components/overview/unavailable";
import { Funnel, type FunnelStage } from "@/components/telemetry/funnel";
import { NormalizationCard } from "@/components/telemetry/normalization-card";
import { SeverityDonut } from "@/components/telemetry/severity-donut";
import { WeeklyArea } from "@/components/telemetry/weekly-area";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/api";
import { fullNumber, percent } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata = { title: "Telemetry · Citalid Risk Engine" };

export default async function TelemetryPage() {
  let data;
  try {
    const [telemetry, frequency] = await Promise.all([api.telemetry(), api.frequency()]);
    data = { telemetry, frequency };
  } catch (error) {
    return (
      <>
        <PageHeader eyebrow="What the feeds saw" title="Telemetry" />
        <ApiUnavailable detail={error instanceof Error ? error.message : String(error)} />
      </>
    );
  }

  const report = data.telemetry.normalization;
  const stages: FunnelStage[] = [
    {
      label: "Raw feed rows",
      value: report.rows_read,
      note: report.feeds
        .map((feed) => `${feed.source.toUpperCase()} ${fullNumber(feed.rows_read)}`)
        .join(" · "),
    },
    {
      label: "Distinct events",
      value: report.total_events,
      note: `${fullNumber(report.duplicates_merged)} duplicate reports absorbed`,
    },
    {
      label: "Attack-grade events",
      value: data.frequency.events_attack_grade,
      note: `severity at or above ${data.frequency.params.severity_threshold}`,
    },
    {
      label: "Episodes",
      value: data.frequency.episodes,
      note: `clustered within ${data.frequency.params.session_window_hours}h per asset and type`,
    },
  ];

  return (
    <>
      <PageHeader
        eyebrow="What the feeds saw"
        title="Telemetry"
        description={`Two feeds delivered ${fullNumber(report.rows_read)} rows describing ${fullNumber(
          report.total_events,
        )} distinct events. The gap between those numbers is ${percent(
          report.inflation_avoided,
        )} of inflation that never reaches the model.`}
      />

      <div className="grid gap-4">
        <Funnel stages={stages} />

        <WeeklyArea weekly={data.telemetry.summary.weekly} />

        <div className="grid gap-4 lg:grid-cols-2">
          <SeverityDonut mix={data.telemetry.summary.severity_mix} />
          <NormalizationCard report={report} />
        </div>
      </div>
    </>
  );
}
