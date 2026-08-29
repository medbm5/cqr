"use client";

import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { ApiUnavailable } from "@/components/overview/unavailable";
import { StatTile } from "@/components/ui/stat-tile";
import { api, type AssetInventoryResponse, type FrequencyResponse, type SeverityClass } from "@/lib/api";
import { fullNumber } from "@/lib/format";

import { ExplanationTrace } from "./explanation-trace";
import { Heatmap } from "./heatmap";
import { LambdaBars } from "./lambda-bars";
import { ParamPanel } from "./param-panel";

export interface FrequencyBundle {
  frequency: FrequencyResponse;
  assets: AssetInventoryResponse;
}

/**
 * The frequency view, with its two conventions as live controls.
 *
 * The initial render comes from the server, so the page is complete before any
 * JavaScript runs. Changing a parameter refetches both endpoints together — they
 * must always describe the same slice — and the charts hold their previous
 * render at reduced opacity while it lands. No skeleton, no layout jump.
 */
export function FrequencyView({ initial }: { initial: FrequencyBundle }) {
  const [bundle, setBundle] = useState(initial);
  const [threshold, setThreshold] = useState<SeverityClass>(
    initial.frequency.params.severity_threshold,
  );
  const [windowHours, setWindowHours] = useState(initial.frequency.params.session_window_hours);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  // A request in flight is abandoned when a newer one starts, so dragging the
  // slider cannot land an out-of-date answer after a newer one.
  const latest = useRef(0);

  const refetch = useCallback((next: { threshold: SeverityClass; windowHours: number }) => {
    const ticket = ++latest.current;
    const params = {
      severity_threshold: next.threshold,
      session_window_hours: next.windowHours,
    };

    Promise.all([api.frequency(params), api.assets(params)])
      .then(([frequency, assets]) => {
        if (ticket !== latest.current) return;
        startTransition(() => {
          setBundle({ frequency, assets });
          setError(null);
        });
      })
      .catch((cause: unknown) => {
        if (ticket !== latest.current) return;
        setError(cause instanceof Error ? cause.message : String(cause));
      });
  }, []);

  const initialised = useRef(false);
  useEffect(() => {
    if (!initialised.current) {
      initialised.current = true;
      return;
    }
    refetch({ threshold, windowHours });
  }, [threshold, windowHours, refetch]);

  const { frequency, assets } = bundle;
  const changed =
    threshold !== frequency.params.severity_threshold ||
    windowHours !== frequency.params.session_window_hours;

  return (
    <>
      <ParamPanel
        threshold={threshold}
        windowHours={windowHours}
        pending={pending || changed}
        onChange={(next) => {
          setThreshold(next.threshold);
          setWindowHours(next.windowHours);
        }}
      />

      {error ? <ApiUnavailable detail={error} /> : null}

      <section aria-label="Frequency headlines" className="mb-4 grid gap-4 sm:grid-cols-3">
        <StatTile
          index={0}
          label="Detected attacks per year"
          value={frequency.lambda_detected}
          format="count"
          term="lambda_detected"
          captionTerm="annualization"
          caption={`Annualized from ${frequency.observed_days} observed days`}
        />
        <StatTile
          index={1}
          label="Episodes observed"
          value={frequency.episodes}
          format="count"
          term="episode"
          captionTerm="attack_grade"
          caption={`From ${fullNumber(frequency.events_attack_grade)} attack-grade events`}
        />
        <StatTile
          index={2}
          label="Loss incidents per year"
          value={frequency.lambda_incident ?? 0}
          format="rate"
          term="lambda_incident"
          captionTerm="p_materialize"
          caption={
            frequency.calibration
              ? `1 in ${fullNumber(Math.round(1 / frequency.calibration.p_materialize))} detected attacks, anchored on ${fullNumber(frequency.calibration.peer_companies)} peer organisations`
              : "Not calibrated"
          }
        />
      </section>

      <div className="grid gap-4">
        <LambdaBars frequency={frequency} dimmed={changed} />
        <Heatmap assets={assets.assets} dimmed={changed} />
        <ExplanationTrace
          lines={frequency.explanation}
          hint={`severity ≥ ${frequency.params.severity_threshold} · ${frequency.params.session_window_hours}h window`}
        />
      </div>
    </>
  );
}
