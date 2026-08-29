import { StatTile } from "@/components/ui/stat-tile";
import { compactEur, fullEur, fullNumber } from "@/lib/format";

export interface Headline {
  totalEvents: number;
  rawRows: number;
  duplicatesMerged: number;
  dedupRate: number;
  lambdaTotal: number;
  episodes: number;
  observedDays: number;
  aal: number;
  medianYear: number;
  simulatedYears: number;
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
      <StatTile
        index={3}
        label="Average annual loss"
        value={headline.aal}
        format="eur"
        caption={`Median year ${compactEur(headline.medianYear)} · ${fullNumber(
          headline.simulatedYears,
        )} simulated years`}
      />
    </section>
  );
}

/** The full figures, for the caption a reader checks the compacted ones against. */
export function headlineFootnote(headline: Headline): string {
  return `AAL ${fullEur(headline.aal)} · ${fullNumber(headline.totalEvents)} distinct events`;
}
