import { PageHeader } from "@/components/ui/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";

export const metadata = { title: "Frequency · Citalid Risk Engine" };

export default function FrequencyPage() {
  return (
    <>
      <PageHeader eyebrow="How often attacks land" title="Frequency" description="Episodes per asset and attack type, annualized on the observed window, with the conventions exposed as controls." />
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
