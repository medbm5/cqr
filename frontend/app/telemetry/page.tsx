import { PageHeader } from "@/components/ui/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";

export const metadata = { title: "Telemetry · Citalid Risk Engine" };

export default function TelemetryPage() {
  return (
    <>
      <PageHeader eyebrow="What the feeds saw" title="Telemetry" description="Normalization accounting, weekly event volume per feed, and the severity mix behind every downstream rate." />
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
