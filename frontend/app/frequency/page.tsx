import { FrequencyView } from "@/components/frequency/frequency-view";
import { ApiUnavailable } from "@/components/overview/unavailable";
import { PageHeader } from "@/components/ui/page-header";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata = { title: "Frequency · Citalid Risk Engine" };

export default async function FrequencyPage() {
  let initial;
  try {
    const [frequency, assets] = await Promise.all([api.frequency(), api.assets()]);
    initial = { frequency, assets };
  } catch (error) {
    return (
      <>
        <PageHeader eyebrow="How often attacks land" title="Frequency" />
        <ApiUnavailable detail={error instanceof Error ? error.message : String(error)} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="How often attacks land"
        title="Frequency"
        description="An alert is not an attack. Attack-grade events are clustered into episodes per asset — one machine in one window is one attack — then scaled to a year and calibrated against the peer incident rate. Both conventions below are judgment calls, so both are controls."
      />
      <FrequencyView initial={initial} />
    </>
  );
}
