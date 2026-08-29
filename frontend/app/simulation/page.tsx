import { ApiUnavailable } from "@/components/overview/unavailable";
import { SimulationView } from "@/components/simulation/simulation-view";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = { title: "Simulation · Citalid Risk Engine" };

export default async function SimulationPage() {
  let initial;
  try {
    // No n_years, seed or sensitivity_years: the defaults are what the server
    // warms at boot, so the first render is served from cache. The reader picks
    // a different size from the run panel, which then does compute.
    initial = await api.simulate({ curve_points: 160, histogram_bins: 44 });
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
