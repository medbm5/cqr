/**
 * Plain-language explanations for every mathematical concept the UI shows.
 *
 * One source of truth: no tooltip copy is written inline anywhere. A term that
 * appears on three pages is explained once here, so the three can never drift
 * into saying different things about the same number.
 *
 * The register is deliberate — one or two short sentences, concrete, for a
 * smart reader who is not a statistician. Formulas only where they are tiny
 * enough to read at a glance.
 */

export interface GlossaryEntry {
  /** The concept's display name. */
  term: string;
  /** One or two sentences, in plain language. */
  hint: string;
}

export const GLOSSARY = {
  aal: {
    term: "Average annual loss",
    hint: "The average cost of a year, across all simulated years — including the many that cost €0. What you'd budget per year over the long run.",
  },
  median_year: {
    term: "Median year",
    hint: "The middle year: half the simulated years cost less, half cost more. €0 here means most years have no incident at all.",
  },
  var95: {
    term: "VaR 95",
    hint: "The loss a 1-in-20 year reaches. 95% of years stay below this line.",
  },
  var99: {
    term: "VaR 99",
    hint: "The loss a 1-in-100 year reaches. 99% of years stay below this line.",
  },
  tvar95: {
    term: "TVaR 95",
    hint: "The average of the worst 5% of years. VaR says where the bad zone starts; TVaR says how bad it is on average once inside.",
  },
  tvar99: {
    term: "TVaR 99",
    hint: "The average of the worst 1% of years — the catastrophe scenario average.",
  },
  poisson: {
    term: "Poisson process",
    hint: "Turns an average rate (0.31 incidents/yr) into probabilities: most years get 0 incidents, some get 1, a few get more.",
  },
  lognormal: {
    term: "Lognormal distribution",
    hint: "A distribution for values that can't go below zero but can explode upward — the logarithm of the loss follows a bell curve. Standard for financial losses.",
  },
  mu: {
    term: "μ (mu)",
    hint: "The average of the log-losses among weighted peers. exp(μ) gives the median incident cost.",
  },
  sigma: {
    term: "σ (sigma)",
    hint: "The spread of the log-losses. Large σ = losses span several orders of magnitude, and the mean sits far above the median.",
  },
  median_incident: {
    term: "Median incident cost",
    hint: "Half of comparable incidents cost less than this, half more. The 'typical' incident, ignoring extremes.",
  },
  mean_incident: {
    term: "Mean incident cost",
    hint: "The average incident cost, pulled up by rare catastrophes. exp(μ + σ²/2) — this is what feeds the annual average.",
  },
  kish_neff: {
    term: "Effective sample size",
    hint: "How many fully-relevant incidents the weighted sample is worth. 78 incidents with unequal voices carry the information of 52 equal ones.",
  },
  fallback: {
    term: "Pooled fallback",
    hint: "If a type has fewer than 30 effective incidents, its own fit is too fragile — it inherits the distribution fitted on all incidents instead.",
  },
  peer_weight: {
    term: "Peer weighting",
    hint: "Each incident counts in proportion to how much its organisation resembles this one: sector, size band, and security maturity.",
  },
  episode: {
    term: "Episode",
    hint: "One attack, reconstructed from its alerts: all high-severity events on one asset with no quiet gap longer than the session window.",
  },
  session_window: {
    term: "Session window",
    hint: "The silence that separates two attacks on the same asset. A gap longer than this closes an episode; the next alert opens a new one.",
  },
  annualization: {
    term: "Annualization",
    hint: "Observed 212 days, need a year: counts are scaled by 365/212. Valid because the weekly rate is flat.",
  },
  lambda_detected: {
    term: "Detected attack rate",
    hint: "Attack episodes per year, as seen by the sensors, annualized from the observed window.",
  },
  lambda_incident: {
    term: "Loss incident rate",
    hint: "Loss-causing incidents per year: detected attacks × the probability one materializes, anchored on the peer base.",
  },
  p_materialize: {
    term: "p_materialize",
    hint: "The share of detected attacks that end in an actual loss — calibrated so this company matches the incident rate of 1,310 comparable organisations.",
  },
  ks: {
    term: "Kolmogorov–Smirnov distance",
    hint: "The largest gap between the fitted curve and the observed data, on a 0–1 scale. Small = the fit tracks the evidence.",
  },
  qq_plot: {
    term: "QQ plot",
    hint: "Each dot asks one incident: are you where the fitted distribution predicts? Dots on the diagonal mean yes.",
  },
  seed: {
    term: "Random seed",
    hint: "Fixes the random draws: same seed, same parameters, exactly the same results. Change it to check conclusions survive.",
  },
  monte_carlo: {
    term: "Monte Carlo simulation",
    hint: "Roll thousands of possible years and look at the pile: frequency dice decide how many incidents, severity dice price each one.",
  },
  dedup: {
    term: "Cross-feed deduplication",
    hint: "The same real event reported by two tools is counted once — the worst severity grade wins.",
  },
  attack_grade: {
    term: "Attack-grade event",
    hint: "Events with severity High or Critical — the subset treated as attack signal rather than background noise.",
  },
} as const satisfies Record<string, GlossaryEntry>;

/** Every concept the UI can explain. A typo becomes a type error. */
export type GlossaryKey = keyof typeof GLOSSARY;

export const GLOSSARY_KEYS = Object.keys(GLOSSARY) as GlossaryKey[];
