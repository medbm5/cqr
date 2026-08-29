"use client";

import { motion } from "framer-motion";
import { useState } from "react";

import { HintTip } from "@/components/HintTip";
import { Card, CardHeader } from "@/components/ui/card";
import { StatTile } from "@/components/ui/stat-tile";
import type { AttackType, SeverityResponse } from "@/lib/api";
import { fullEur, fullNumber } from "@/lib/format";

import { FitHistogram } from "./fit-histogram";
import { QqPlot } from "./qq-plot";

const LABELS: Record<AttackType, string> = {
  ransomware: "Ransomware",
  data_breach: "Data breach",
  credential_theft: "Credential theft",
  ddos: "DDoS",
  phishing: "Phishing",
  misconfiguration: "Misconfiguration",
  insider_error: "Insider error",
  supply_chain: "Supply chain",
  other: "Other",
};

/** The severity model, one attack type at a time. */
export function SeverityView({ severity }: { severity: SeverityResponse }) {
  const ordered = [...severity.fits].sort((a, b) => b.mean_eur - a.mean_eur);
  const [selected, setSelected] = useState(ordered[0]?.attack_type ?? "ransomware");
  const fit = ordered.find((candidate) => candidate.attack_type === selected) ?? ordered[0];

  if (!fit) return null;

  const peers = severity.peer_weighting;

  return (
    <>
      {/* Tabs, not a dropdown: nine types, and the reader is comparing them. */}
      <div
        role="tablist"
        aria-label="Attack type"
        className="mb-6 flex gap-1 overflow-x-auto border-b border-navy-800 pb-px"
      >
        {ordered.map((candidate) => {
          const active = candidate.attack_type === selected;
          return (
            <button
              key={candidate.attack_type}
              role="tab"
              type="button"
              aria-selected={active}
              onClick={() => setSelected(candidate.attack_type)}
              className={[
                "relative shrink-0 rounded-t-lg px-3 py-2 text-sm transition-colors duration-200",
                active ? "text-ink" : "text-ink-secondary hover:text-ink",
              ].join(" ")}
            >
              {LABELS[candidate.attack_type] ?? candidate.attack_type}
              {active ? (
                <motion.span
                  layoutId="severity-tab"
                  aria-hidden
                  className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
                  transition={{ type: "spring", stiffness: 400, damping: 34 }}
                />
              ) : null}
            </button>
          );
        })}
      </div>

      <section aria-label="Fitted parameters" className="mb-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          index={0}
          label="Typical incident (median)"
          value={fit.median_eur}
          format="eur"
          term="median_incident"
          captionTerm="mu"
          caption={`exp(μ) with μ = ${fit.mu.toFixed(3)}`}
        />
        <StatTile
          index={1}
          label="Average incident (mean)"
          value={fit.mean_eur}
          format="eur"
          term="mean_incident"
          captionTerm="sigma"
          caption={`exp(μ + σ²/2), σ = ${fit.sigma.toFixed(3)}`}
        />
        <StatTile
          index={2}
          label="Peer incidents"
          value={fit.observations}
          format="count"
          term="peer_weight"
          caption={
            fit.used_pooled
              ? "Too thin to fit alone — priced at the pooled rate"
              : `of ${fullNumber(severity.incidents_fitted)} with a usable loss`
          }
        />
        <StatTile
          index={3}
          label="Effective sample"
          value={fit.effective_n}
          format="count"
          term="kish_neff"
          captionTerm="fallback"
          caption={`Kish n_eff; the fallback threshold is ${severity.min_effective_n}`}
        />
      </section>

      {fit.used_pooled ? (
        <p className="mb-4 rounded-lg border border-caution/30 bg-caution/5 px-4 py-3 text-xs leading-relaxed text-ink-secondary">
          <span className="font-semibold text-caution">
            Pooled fallback
            <HintTip term="fallback" />.
          </span>{" "}
          {fit.observations === 0
            ? "The incident base holds no incidents of this type, so it is priced at the pooled rate across every type."
            : `Its effective sample size is below ${severity.min_effective_n}, so it is priced at the pooled rate rather than on parameters a thin sample would make look confident.`}
        </p>
      ) : null}

      <div className="grid gap-4">
        <FitHistogram fit={fit} />

        <div className="grid gap-4 lg:grid-cols-2">
          <QqPlot fit={fit} />

          <Card>
            <CardHeader
              title="Peer group"
              hint="Soft weighting, never a hard filter"
              term="peer_weight"
            />
            <div className="space-y-4 px-5 py-4">
              <p className="text-xs leading-relaxed text-ink-secondary">
                Filtering to exact peers keeps 112 of {fullNumber(severity.incidents_fitted)}{" "}
                incidents and leaves no attack type with a credible sample. Every incident
                contributes instead, weighted by how much it resembles the target.
              </p>

              <div className="rounded-lg border border-navy-800 bg-navy-950/50 px-3 py-2.5">
                <p className="font-mono text-xs leading-relaxed text-ink">
                  w = w<sub>sector</sub> × w<sub>size</sub> × exp(−d² / 2h²)
                </p>
              </div>

              <dl className="space-y-2 text-xs">
                {[
                  {
                    name: "Sector",
                    value: `${peers.sector_match_weight} if ${peers.target_sector}, else ${peers.sector_other_weight}`,
                  },
                  {
                    name: "Size",
                    value: `${peers.size_match_weight} if ${peers.target_size}, else ${peers.size_other_weight}`,
                  },
                  {
                    name: "Maturity",
                    value: `Gaussian kernel on |maturity − ${peers.target_maturity}|, h = ${peers.maturity_bandwidth}`,
                  },
                ].map((row) => (
                  <div key={row.name} className="flex gap-3">
                    <dt className="w-16 shrink-0 font-medium text-ink-secondary">{row.name}</dt>
                    <dd className="min-w-0 text-ink-muted">{row.value}</dd>
                  </div>
                ))}
              </dl>

              <p className="border-t border-navy-800 pt-3 text-xs leading-relaxed text-ink-muted">
                Kish effective sample size measures how <em>evenly</em> weight is spread, not
                how large it is: forty peers all discounted equally still count as forty. What
                collapses it is one close peer among many distant ones.
              </p>

              <div className="flex items-baseline justify-between border-t border-navy-800 pt-3">
                <span className="text-xs text-ink-secondary">Pooled fallback distribution</span>
                <span className="tabular text-xs font-semibold text-ink">
                  {fullEur(severity.pooled.median_eur)} median
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
