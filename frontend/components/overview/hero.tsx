import { Card } from "@/components/ui/card";

/** The company the whole model is about. */
const PROFILE = [
  { label: "Size band", value: "ETI" },
  { label: "Sector", value: "Retail / e-commerce" },
  { label: "Employees", value: "1,200" },
  { label: "Security maturity", value: "55 / 100" },
] as const;

/**
 * The landing hero: who is being assessed, before any number about them.
 *
 * The profile is not decoration — it is the peer-weighting target. Every
 * severity figure downstream is calibrated toward these four attributes, so
 * showing them first is showing the model's main assumption.
 */
export function Hero() {
  return (
    <section className="mb-10">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-accent">
        Cyber risk quantification
      </p>
      <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-ink sm:text-4xl">
        What a year of cyber attacks costs this company
      </h1>
      <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-secondary sm:text-base">
        Annualized loss estimated from seven months of SIEM and EDR telemetry, priced
        against 1,600 incidents at comparable organisations. Every figure below is
        reconstructable from its inputs.
      </p>

      <Card className="mt-7 overflow-hidden">
        <dl className="grid grid-cols-2 divide-navy-800 sm:grid-cols-4 sm:divide-x">
          {PROFILE.map(({ label, value }) => (
            <div key={label} className="px-5 py-4">
              <dt className="text-xs font-medium text-ink-muted">{label}</dt>
              <dd className="mt-1 text-sm font-semibold text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </section>
  );
}
