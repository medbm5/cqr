import { FadeIn } from "@/components/fade-in";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-24">
      <FadeIn>
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent">
          Cyber risk quantification
        </p>
        <h1 className="mt-4 text-5xl font-semibold tracking-tight text-white">
          Citalid Risk Engine
        </h1>
        <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-400">
          Annualized loss estimation from SIEM and EDR telemetry, calibrated on an
          external incident base. Every figure is reconstructable from its inputs.
        </p>
      </FadeIn>
    </main>
  );
}
