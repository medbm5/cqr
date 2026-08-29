"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";

import { HintTip } from "@/components/HintTip";
import { ApiUnavailable } from "@/components/overview/unavailable";
import { ExplanationTrace } from "@/components/frequency/explanation-trace";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { Card } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import { api, type SimulationResponse } from "@/lib/api";
import { compactEur, fullEur, fullNumber, percent } from "@/lib/format";

import { ExceedanceCurves } from "./exceedance-curves";
import { LossHistogram } from "./loss-histogram";
import { SensitivityGrid } from "./sensitivity-grid";

const YEAR_CHOICES = [1_000, 5_000, 25_000, 50_000, 100_000] as const;

/**
 * The run panel and everything it produces.
 *
 * The first result arrives from the server so the page is never empty. Running
 * again is deliberate — the simulation takes seconds, so it is a button rather
 * than something a slider triggers by accident.
 */
export function SimulationView({ initial }: { initial: SimulationResponse }) {
  const [result, setResult] = useState(initial);
  const [years, setYears] = useState<number>(initial.n_years);
  const [seed, setSeed] = useState(initial.seed);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();
  const started = useRef(0);

  // Real elapsed time, not a fabricated percentage. The engine cannot report
  // progress, and a bar that invents one is a bar that lies.
  useEffect(() => {
    if (!running) return;
    started.current = Date.now();
    const timer = window.setInterval(
      () => setElapsed((Date.now() - started.current) / 1000),
      100,
    );
    return () => window.clearInterval(timer);
  }, [running]);

  const run = useCallback(() => {
    setRunning(true);
    setError(null);
    setElapsed(0);
    api
      .simulate({
        n_years: years,
        seed,
        curve_points: 160,
        histogram_bins: 44,
      })
      .then(setResult)
      .catch((cause: unknown) =>
        setError(cause instanceof Error ? cause.message : String(cause)),
      )
      .finally(() => setRunning(false));
  }, [years, seed]);

  const { metrics } = result;
  const stale = result.n_years !== years || result.seed !== seed;

  // Staggered reveal: the hero lands first, then the tiles, then the charts.
  const reveal = (index: number) => ({
    initial: reduceMotion ? false : { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.3, delay: reduceMotion ? 0 : 0.1 + index * 0.08, ease: [0.16, 1, 0.3, 1] as const },
  });

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end gap-x-8 gap-y-4 rounded-xl border border-navy-800 bg-navy-900 px-5 py-4">
        <div>
          {/* Beside the label, not inside it: a button in a `for`-bound label
              activates the control it labels. */}
          <div className="flex items-baseline">
            <label htmlFor="years" className="text-xs font-medium text-ink-secondary">
              Simulated years
            </label>
            <HintTip term="monte_carlo" />
          </div>
          <select
            id="years"
            value={years}
            onChange={(event) => setYears(Number(event.target.value))}
            className="mt-1.5 rounded-lg border border-navy-700 bg-navy-850 px-3 py-1.5 text-sm text-ink transition-colors hover:border-navy-600"
          >
            {YEAR_CHOICES.map((choice) => (
              <option key={choice} value={choice}>
                {fullNumber(choice)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="flex items-baseline">
            <label htmlFor="seed" className="text-xs font-medium text-ink-secondary">
              Seed
            </label>
            <HintTip term="seed" />
          </div>
          <input
            id="seed"
            type="number"
            min={0}
            value={seed}
            onChange={(event) => setSeed(Math.max(0, Number(event.target.value)))}
            className="tabular mt-1.5 w-28 rounded-lg border border-navy-700 bg-navy-850 px-3 py-1.5 text-sm text-ink transition-colors hover:border-navy-600"
          />
        </div>

        <button
          type="button"
          onClick={run}
          disabled={running}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-navy-950 transition-all duration-200 hover:bg-accent-strong disabled:cursor-wait disabled:opacity-60"
        >
          {running ? "Running…" : stale ? "Run simulation" : "Run again"}
        </button>

        <div className="min-w-40 flex-1" aria-live="polite">
          {running ? (
            <>
              {/* Indeterminate on purpose: the engine reports no progress, so a
                  percentage would be invented. Elapsed seconds are real. */}
              <div className="h-1 overflow-hidden rounded-full bg-navy-700">
                <motion.div
                  className="h-full w-1/3 rounded-full bg-accent"
                  animate={{ x: ["-100%", "300%"] }}
                  transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
                />
              </div>
              <p className="tabular mt-2 text-xs text-ink-muted">
                {fullNumber(years)} years · {elapsed.toFixed(1)}s
              </p>
            </>
          ) : (
            <p className="text-xs text-ink-muted">
              {stale
                ? "Parameters changed — run to refresh"
                : `Seed ${result.seed} · ${fullNumber(result.n_years)} years`}
            </p>
          )}
        </div>
      </div>

      {error ? (
        <div className="mb-4">
          <ApiUnavailable detail={error} />
        </div>
      ) : null}

      <AnimatePresence mode="wait">
        <motion.div key={`${result.n_years}-${result.seed}`} className="grid gap-4">
          {/* The hero figure: exactly one per view, in the same sans as
              everything else, with proportional digits. */}
          <motion.div {...reveal(0)}>
            <Card className="px-6 py-8 sm:px-8 sm:py-10">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-accent">
                Average annual loss
                <HintTip term="aal" />
              </p>
              <AnimatedCounter
                value={metrics.aal}
                format={compactEur}
                durationMs={1100}
                className="mt-3 block text-5xl font-semibold tracking-tight text-ink sm:text-6xl"
              />
              <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-secondary">
                {fullEur(metrics.aal)} a year across {fullNumber(result.n_years)} simulated
                years. A median year
                <HintTip term="median_year" /> costs {fullEur(metrics.median)}
                {metrics.median > 0
                  ? `, so the mean sits ${(metrics.aal / metrics.median).toFixed(1)}× above the typical one.`
                  : "."}
              </p>
              <CapNote cap={result.loss_cap} aal={metrics.aal} />
            </Card>
          </motion.div>

          <motion.section
            {...reveal(1)}
            aria-label="Risk metrics"
            className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <StatTile
              index={0}
              label="VaR 95"
              term="var95"
              value={metrics.var_95}
              format="eur"
              caption="A 1-in-20 year reaches this"
            />
            <StatTile
              index={1}
              label="TVaR 95"
              term="tvar95"
              value={metrics.tvar_95}
              format="eur"
              caption="Mean of the worst 5% of years"
            />
            <StatTile
              index={2}
              label="VaR 99"
              term="var99"
              value={metrics.var_99}
              format="eur"
              caption="A 1-in-100 year reaches this"
            />
            <StatTile
              index={3}
              label="TVaR 99"
              term="tvar99"
              value={metrics.tvar_99}
              format="eur"
              caption="Mean of the worst 1% of years"
            />
          </motion.section>

          <motion.div {...reveal(2)}>
            <LossHistogram
              histogram={result.histogram}
              metrics={metrics}
              cap={result.loss_cap}
              years={result.n_years}
            />
          </motion.div>

          <motion.div {...reveal(3)}>
            <ExceedanceCurves aep={result.aep_curve} oep={result.oep_curve} />
          </motion.div>

          {result.sensitivity ? (
            <motion.div {...reveal(4)}>
              <SensitivityGrid grid={result.sensitivity} />
            </motion.div>
          ) : null}

          <motion.div {...reveal(5)}>
            <WhyThisNumber lines={result.explanation} />
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </>
  );
}

/**
 * What the plausibility cap cost, stated beside the figure it changed.
 *
 * A cap that removes a third of the AAL is not an implementation detail. It is
 * reported next to the headline rather than buried in the trace, because a
 * reader comparing this number against an uncapped one elsewhere needs to know
 * which they are looking at without opening anything.
 */
function CapNote({
  cap,
  aal,
}: {
  cap: SimulationResponse["loss_cap"];
  aal: number;
}) {
  if (cap.draws_capped === 0) {
    return (
      <p className="mt-4 text-xs leading-relaxed text-ink-muted">
        No single incident reached the {compactEur(cap.cap_eur)} plausibility ceiling, so the cap
        changed nothing in this run.
      </p>
    );
  }

  // One string rather than interleaved JSX: six interpolations in two
  // sentences, most of them butted against punctuation, read as a sentence here
  // and as a jigsaw in JSX.
  const source =
    cap.quantile === null
      ? "set for this run"
      : `the ${(cap.quantile * 100).toFixed(1)}th percentile of what comparable organisations were actually observed to lose`;

  return (
    <p className="mt-4 max-w-2xl text-xs leading-relaxed text-ink-muted">
      {`Each incident is capped at ${compactEur(cap.cap_eur)} — ${source}. ` +
        `${fullNumber(cap.draws_capped)} of ${fullNumber(cap.draws_total)} drawn incidents ` +
        `(${percent(cap.share_capped, 2)}) hit it, removing ${percent(cap.aal_reduction)} of the ` +
        `uncapped average: ${fullEur(cap.aal_uncapped)} against ${fullEur(aal)}.`}
    </p>
  );
}

/** The trace, collapsed by default — available on demand, never in the way. */
function WhyThisNumber({ lines }: { lines: string[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between rounded-xl border border-navy-800 bg-navy-900 px-5 py-4 text-left transition-colors duration-200 hover:border-navy-700"
      >
        <span>
          <span className="block text-sm font-semibold text-ink">Why this number</span>
          <span className="mt-0.5 block text-xs text-ink-muted">
            The engine&apos;s own trace, from lambda and sigma through to the metrics
          </span>
        </span>
        <span aria-hidden className="text-xs text-accent">
          {open ? "Hide" : "Show"}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open ? (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="pt-3">
              <ExplanationTrace lines={lines} title="Simulation trace" />
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
