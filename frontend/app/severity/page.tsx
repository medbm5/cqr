import { PageHeader } from "@/components/ui/page-header";
import { CardSkeleton } from "@/components/ui/skeleton";

export const metadata = { title: "Severity · Citalid Risk Engine" };

export default function SeverityPage() {
  return (
    <>
      <PageHeader eyebrow="What one attack costs" title="Severity" description="Fitted loss distributions per attack type, the peer weighting behind them, and the diagnostics challenging each fit." />
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
