import { Hero } from "@/components/overview/hero";
import { KpiRow, type Headline } from "@/components/overview/kpi-row";
import { ApiUnavailable } from "@/components/overview/unavailable";
import { Card, CardHeader } from "@/components/ui/card";
import { NAV_ITEMS } from "@/components/shell/nav-items";
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

/** Years simulated for the landing figure: enough for a stable mean, fast enough to load. */
const LANDING_YEARS = 10_000;

async function loadHeadline(): Promise<Headline | { error: string }> {
  try {
    const [telemetry, frequency, simulation] = await Promise.all([
      api.telemetry(),
      api.frequency(),
      // The tail is not on this page, so the curves are requested at their
      // minimum and the sensitivity sweep is skipped.
      api.simulate({
        n_years: LANDING_YEARS,
        curve_points: 2,
        include_sensitivity: false,
      }),
    ]);

    const report = telemetry.normalization;
    return {
      totalEvents: report.total_events,
      rawRows: report.rows_read,
      duplicatesMerged: report.duplicates_merged,
      dedupRate: report.duplicates_merged / report.rows_read,
      lambdaTotal: frequency.lambda_total,
      episodes: frequency.episodes,
      observedDays: frequency.observed_days,
      aal: simulation.metrics.aal,
      medianYear: simulation.metrics.median,
      simulatedYears: simulation.n_years,
    };
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
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
