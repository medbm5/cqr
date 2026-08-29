import Link from "next/link";

import { StatTile } from "@/components/ui/stat-tile";
import { compactEur, fullNumber } from "@/lib/format";

export interface Headline {
  totalEvents: number;
  rawRows: number;
  duplicatesMerged: number;
  dedupRate: number;
  lambdaTotal: number;
  episodes: number;
  observedDays: number;
  /** Null while the engine is still computing it, or if that one call failed. */
  loss: { aal: number; medianYear: number; simulatedYears: number } | null;
}

/**
 * The four figures the whole case study reduces to.
 *
 * Ordered as the pipeline runs — what was observed, what survived
 * deduplication, how often attacks land, what a year costs — so reading left to
 * right is reading the argument.
 */
export function KpiRow({ headline }: { headline: Headline }) {
  return (
    <section aria-label="Headline figures" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatTile
        index={0}
        label="Distinct events"
        value={headline.totalEvents}
        format="count"
        caption={`From ${fullNumber(headline.rawRows)} raw rows across two feeds`}
      />
      <StatTile
        index={1}
        label="Deduplicated"
        value={headline.dedupRate}
        format="percent"
        delta={{
          label: `${fullNumber(headline.duplicatesMerged)} rows`,
          direction: "down",
          isGood: true,
          versus: "naive concatenation",
        }}
      />
      <StatTile
        index={2}
        label="Attack frequency"
        value={headline.lambdaTotal}
        format="perYear"
        caption={`${fullNumber(headline.episodes)} episodes over ${headline.observedDays} observed days`}
      />
      {headline.loss ? (
        <StatTile
          index={3}
          label="Average annual loss"
          value={headline.loss.aal}
          format="eur"
          caption={`Median year ${compactEur(headline.loss.medianYear)} · ${fullNumber(
            headline.loss.simulatedYears,
          )} simulated years`}
        />
      ) : (
        <PendingTile />
      )}
    </section>
  );
}

/**
 * Stands in for the loss figure while the engine is still warming.
 *
 * Deliberately not a zero and not a skeleton that never resolves: it says which
 * figure is missing and why, so a reader is never left wondering whether the
 * answer is "nothing" or "not yet".
 */
function PendingTile() {
  return (
    <div className="rounded-xl border border-navy-800 bg-navy-900 p-5 shadow-card">
      <p className="text-xs font-medium text-ink-secondary">Average annual loss</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-ink-muted">—</p>
      <p className="mt-2 text-xs text-ink-muted">
        The simulation is still warming up. Reload in a minute, or open{" "}
        <Link href="/simulation" className="text-accent underline-offset-2 hover:underline">
          Simulation
        </Link>
        .
      </p>
    </div>
  );
}
