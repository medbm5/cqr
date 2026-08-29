import { PageHeader } from "@/components/ui/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";

export const metadata = { title: "Simulation · Citalid Risk Engine" };

export default function SimulationPage() {
  return (
    <>
      <PageHeader eyebrow="What a year costs" title="Simulation" description="Monte Carlo annual loss, AAL against VaR and TVaR, the exceedance curves and the parameter sensitivity grid." />
      <div className="grid gap-4 lg:grid-cols-2">
        <CardSkeleton lines={5} />
        <CardSkeleton lines={5} />
      </div>
      <p className="mt-6 text-xs text-ink-muted">
        This view is not built yet. The data behind it is already served by the API.
      </p>
    </>
  );
}
