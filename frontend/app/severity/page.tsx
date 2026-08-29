import { ApiUnavailable } from "@/components/overview/unavailable";
import { SeverityView } from "@/components/severity/severity-view";
import { ExplanationTrace } from "@/components/frequency/explanation-trace";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/api";
import { fullNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

export const metadata = { title: "Severity · Citalid Risk Engine" };

export default async function SeverityPage() {
  let severity;
  try {
    severity = await api.severity();
  } catch (error) {
    return (
      <>
        <PageHeader eyebrow="What one attack costs" title="Severity" />
        <ApiUnavailable detail={error instanceof Error ? error.message : String(error)} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="What one attack costs"
        title="Severity"
        description={`A lognormal fitted per attack type on ${fullNumber(
          severity.incidents_fitted,
        )} external incidents, each weighted by how much its organisation resembles this one. Every fit ships with the evidence against it.`}
      />
      <SeverityView severity={severity} />
      <div className="mt-4">
        <ExplanationTrace lines={severity.explanation} hint="Cleaning, weighting, fitting, challenging" />
      </div>
    </>
  );
}
