import { Hero } from "@/components/overview/hero";
import { KpiRow, type Headline } from "@/components/overview/kpi-row";
import { ApiUnavailable } from "@/components/overview/unavailable";
import { NAV_ITEMS } from "@/components/shell/nav-items";
import { Card, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api";
import Link from "next/link";

/**
 * Rendered per request, never prerendered.
 *
 * These figures come from a live engine. Statically baking them at build time
 * would ship whatever the API happened to say then - or, if it was not running,
 * a permanently cached "unavailable" page.
 */
export const dynamic = "force-dynamic";

function describe(reason: unknown): string {
  return reason instanceof Error ? reason.message : String(reason);
}

async function loadHeadline(): Promise<Headline | { error: string }> {
  // The two cheap reads decide whether the page can render at all. The
  // simulation is the expensive one - on a small instance it can still be
  // warming up - so it is fetched alongside them and allowed to fail without
  // taking the rest of the page down. Losing one figure is not losing the page.
  const [telemetry, frequency, simulation] = await Promise.allSettled([
    api.telemetry(),
    api.frequency(),
    api.simulate({ curve_points: 2 }),
  ]);

  if (telemetry.status === "rejected") {
    return { error: describe(telemetry.reason) };
  }
  if (frequency.status === "rejected") {
    return { error: describe(frequency.reason) };
  }

  const report = telemetry.value.normalization;
  return {
    totalEvents: report.total_events,
    rawRows: report.rows_read,
    duplicatesMerged: report.duplicates_merged,
    dedupRate: report.duplicates_merged / report.rows_read,
    lambdaTotal: frequency.value.lambda_total,
    episodes: frequency.value.episodes,
    observedDays: frequency.value.observed_days,
    loss:
      simulation.status === "fulfilled"
        ? {
            aal: simulation.value.metrics.aal,
            medianYear: simulation.value.metrics.median,
            simulatedYears: simulation.value.n_years,
          }
        : null,
  };
}

export default async function Overview() {
  const headline = await loadHeadline();

  return (
    <>
      <Hero />

      {"error" in headline ? (
        <ApiUnavailable detail={headline.error} />
      ) : (
        <KpiRow headline={headline} />
      )}

      <section className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {NAV_ITEMS.filter((item) => item.href !== "/").map((item) => (
          <Link key={item.href} href={item.href} className="block rounded-xl">
            <Card interactive className="h-full p-5">
              <h2 className="text-sm font-semibold text-ink">{item.label}</h2>
              <p className="mt-1.5 text-xs leading-relaxed text-ink-secondary">{item.hint}</p>
              <p aria-hidden className="mt-4 text-xs font-medium text-accent">
                Open →
              </p>
            </Card>
          </Link>
        ))}
      </section>

      <Card className="mt-10">
        <CardHeader title="How the estimate is built" hint="Four stages, each auditable" />
        <ol className="grid gap-px overflow-hidden bg-navy-800 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              step: "Ingestion",
              body: "Two feeds deduplicated on asset, technique and timestamp. Concatenating them would overstate every rate.",
            },
            {
              step: "Frequency",
              body: "Attack-grade events clustered into episodes per asset and attack type, then annualized on the observed window.",
            },
            {
              step: "Severity",
              body: "A lognormal per attack type, fitted on incidents weighted by how much they resemble this company.",
            },
            {
              step: "Simulation",
              body: "Poisson counts against fitted losses, compounded over tens of thousands of simulated years.",
            },
          ].map(({ step, body }, index) => (
            <li key={step} className="bg-navy-900 p-5">
              <p className="text-xs font-medium tabular text-ink-muted">
                {String(index + 1).padStart(2, "0")}
              </p>
              <p className="mt-2 text-sm font-semibold text-ink">{step}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-ink-secondary">{body}</p>
            </li>
          ))}
        </ol>
      </Card>
    </>
  );
}
