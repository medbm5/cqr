import { ApiUnavailable } from "@/components/overview/unavailable";
import { SimulationView } from "@/components/simulation/simulation-view";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = { title: "Simulation · Citalid Risk Engine" };

/** Small enough to render the page quickly; the reader can run a longer one. */
const INITIAL_YEARS = 5_000;

export default async function SimulationPage() {
  let initial;
  try {
    initial = await api.simulate({
      n_years: INITIAL_YEARS,
      seed: 42,
      curve_points: 160,
      histogram_bins: 44,
      include_sensitivity: true,
      sensitivity_years: 5_000,
    });
  } catch (error) {
    return (
      <>
        <PageHeader eyebrow="What a year costs" title="Simulation" />
        <ApiUnavailable detail={error instanceof Error ? error.message : String(error)} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="What a year costs"
        title="Simulation"
        description="Each simulated year draws a Poisson count per attack type and a loss per incident, then sums them. Enough years and the total becomes a distribution — which is the only honest answer to what a year costs."
      />
      <SimulationView initial={initial} />
    </>
  );
}
