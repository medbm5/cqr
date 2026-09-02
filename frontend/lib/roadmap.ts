/**
 * What this engine would become with more than four hours.
 *
 * Every modeling entry is a rewrite of an item in `next_steps.md` into one fixed
 * structure — today, the change, the consequence. Nothing here claims a modeling
 * result the repository does not already argue for: the source document is the
 * authority, this file is a projection of it. Platform and data entries are the
 * product work that document does not cover.
 *
 * One source of truth: the page renders this array and nothing else.
 */

export type RoadmapPhase = 1 | 2 | 3;
export type RoadmapTheme = "modeling" | "platform" | "data";
export type RoadmapEffort = "S" | "M" | "L";

export interface RoadmapItem {
  id: string;
  title: string;
  phase: RoadmapPhase;
  theme: RoadmapTheme;
  /** What we have — one honest sentence about today's implementation. */
  current: string;
  /** What to change — concrete and technical. */
  change: string;
  /** How it impacts the project — what the number or the product gains. */
  impact: string;
  effort: RoadmapEffort;
}

export interface PhaseMeta {
  phase: RoadmapPhase;
  title: string;
  summary: string;
}

export const PHASES: PhaseMeta[] = [
  {
    phase: 1,
    title: "Hardening",
    summary:
      "Make the answer defensible before making it bigger. Nothing here changes the model — it changes how much you can trust what it already says.",
  },
  {
    phase: 2,
    title: "Productization",
    summary:
      "Turn one company's case study into something several clients can use, fed by live telemetry rather than a CSV export.",
  },
  {
    phase: 3,
    title: "Model depth",
    summary:
      "The modeling work deliberately left undone, in the order it would most change the number. Each was skipped for a stated reason, not overlooked.",
  },
];

export const ROADMAP: RoadmapItem[] = [
  // ------------------------------------------------- phase 1 — hardening
  {
    id: "backtesting",
    title: "Backtest against the incident base",
    phase: 1,
    theme: "modeling",
    effort: "M",
    current:
      "Nothing validates the output against observed reality. Every check in the suite is internal consistency — invariants, reproducibility, arithmetic.",
    change:
      "Split the telemetry window in half and check that the rate estimated on the first half predicts the second. For severity, hold out a slice of the incident base and score the predicted distribution with a proper scoring rule (CRPS) or a PIT histogram.",
    impact:
      "The first external evidence that the model is calibrated rather than merely self-consistent. The frequency half is cheap and would come first; the severity half is harder than it looks, because the model predicts losses for this company while the held-out incidents belong to others — a naive backtest would score the peer weighting rather than the fit, so doing it properly means leave-one-company-out cross-validation of the weighting scheme itself.",
  },
  {
    id: "ci-pipeline",
    title: "CI pipeline",
    phase: 1,
    theme: "platform",
    effort: "S",
    current:
      "Pre-commit runs ruff and mypy locally. The gates exist and work, but they run on one machine and can be skipped.",
    change:
      "GitHub Actions running `make lint test` on push, a matrix over Python 3.11–3.13, the notebook executed with nbconvert to catch drift between it and the engine, and coverage reported as a check.",
    impact:
      "No effect on the answer — pure infrastructure. What it buys is that the gates stop being optional, and that drift between the notebook's derived constants and the engine's is caught by a machine rather than by someone rereading both.",
  },
  {
    id: "run-history",
    title: "Shared simulation cache and run history",
    phase: 1,
    theme: "platform",
    effort: "M",
    current:
      "Results are memoized with `lru_cache`, which is per-worker and per-process: a multi-worker deployment recomputes the same simulation once per worker, and every cached result dies with the process.",
    change:
      "A shared result store keyed by the full parameter set — seed, years, thresholds, cap — plus a persisted run record so a past run can be reopened by reference instead of recomputed.",
    impact:
      "Identical requests stop costing CPU on every worker, which matters most on exactly the small instances where the recomputation hurts. More usefully, a simulation stops being ephemeral: a run becomes an artifact you can link to, return to and compare against, which is the precondition for the workspace work in phase 2.",
  },

  // -------------------------------------------- phase 2 — productization
  {
    id: "auth-workspaces",
    title: "Authentication and client workspaces",
    phase: 2,
    theme: "platform",
    effort: "L",
    current:
      "A single-tenant demo: one hardcoded company profile, and an open read-only API with no authentication on any path.",
    change:
      "JWT or session auth via Django, and a Company model that owns assets, telemetry, parameters and simulation runs. Every endpoint scoped to the authenticated workspace, with rate limiting on the write path — a 200,000-year request occupies a worker for half a minute.",
    impact:
      "The step from case study to multi-client product. Each client sees only their own estate, their own λ and their own curves; simulation runs become persisted, comparable artifacts belonging to a workspace rather than results that vanish on reload. It also puts the current \"the API has no auth\" on the record as a decision rather than an oversight someone finds later.",
  },
  {
    id: "connectors",
    title: "Data-source integrations",
    phase: 2,
    theme: "data",
    effort: "L",
    current:
      "Two CSV exports, ingested once at startup. The telemetry is a snapshot of seven months that someone exported by hand.",
    change:
      "A pluggable connector layer — Splunk and Elastic for SIEM, CrowdStrike, SentinelOne and Defender for EDR — with scheduled pulls, incremental ingestion and a per-source normalization adapter behind the existing SecurityEvent schema, so the canonical event shape and the deduplication rule stay untouched.",
    impact:
      "Telemetry stays current without a manual export, and the frequency estimate becomes a living number rather than a snapshot. The annualization factor stops being a correction applied to a fixed 212-day window and starts tracking a window that grows on its own.",
  },
  {
    id: "report-export",
    title: "PDF report export",
    phase: 2,
    theme: "platform",
    effort: "M",
    current:
      "The audit trail is excellent on screen and unavailable anywhere else. Everything a reader needs to check a figure lives in a browser tab.",
    change:
      "Render a report server-side from the same result object the UI reads — headline metrics, the charts, and the full numbered explanation chain per stage — as a downloadable artifact stamped with its parameters and seed.",
    impact:
      "The explanations become something you can attach to a board paper or an insurance submission. Given that the whole design principle is that every number is reconstructable from its inputs, a format that survives leaving the app is the natural end of it.",
  },
  {
    id: "observability",
    title: "Monitoring and observability",
    phase: 2,
    theme: "platform",
    effort: "S",
    current:
      "Nothing is instrumented. The 512 MB memory ceiling and the ~4.2 ms per simulated year were found by reproducing failures locally, after the fact.",
    change:
      "Structured request logging, simulation duration and memory as metrics, error tracking, and an alert on the health endpoint.",
    impact:
      "The two production incidents so far — an OOM kill and a gateway timeout — were both diagnosed by rebuilding them on a laptop. Instrumentation turns that guesswork into a first look at a dashboard, and would catch a slow drift in run time long before it becomes a 502.",
  },

  // ------------------------------------------------ phase 3 — model depth
  {
    id: "credibility",
    title: "Gamma-Poisson credibility: blend telemetry with base rates",
    phase: 3,
    theme: "modeling",
    effort: "M",
    current:
      "The engine anchors the incident rate entirely on the peer base — 0.3052 per organisation-year — and lets the telemetry supply only the attack-type mix. Seven months of this company's own telemetry carries zero weight in how often losses happen.",
    change:
      "Treat the per-attack-type rate as λ ~ Gamma(α, β), with the prior set from the incident base and the likelihood from the telemetry episodes. The posterior mean is a credibility-weighted blend, λ = Z·λ_telemetry + (1−Z)·λ_prior with Z = n/(n+k), and Z rises as the observation window lengthens.",
    impact:
      "An estate genuinely attacked twice as often as its peers is currently priced identically to one that is not. The blend gives this company's own evidence real but not total weight — a middle ground between the old model, which trusted the telemetry completely, and the current one, which does not trust it at all. It was not built because nothing in the data pins k, and choosing one by feel would quietly decide how much a client's own evidence counts. It is still the first thing to build next.",
  },
  {
    id: "gpd-tail",
    title: "GPD tail via peaks-over-threshold",
    phase: 3,
    theme: "modeling",
    effort: "M",
    current:
      "The severity stage already reports that a Pareto tail describes the extremes better than the fitted lognormal on five of eight attack types, twice with α < 1 — and then fits the lognormal anyway.",
    change:
      "A spliced severity distribution: lognormal body below a threshold u, generalised Pareto above it, fitted by maximum likelihood on the exceedances, with u chosen from a mean-residual-life plot rather than a fixed quantile. sample() draws from the mixture.",
    impact:
      "VaR 99 and TVaR 99 are made almost entirely of that tail, so they are currently understated by an unknown margin. It was not done because three of the eight types have fewer than 15 exceedances above the weighted 90th percentile — including data_breach, which has the second-largest mean and therefore the tail most worth modelling. Fitting a GPD to a dozen points produces a shape parameter with enormous variance, so the honest move was to report the diagnostic and leave the fit alone.",
  },
  {
    id: "copulas",
    title: "Dependence between attack types",
    phase: 3,
    theme: "modeling",
    effort: "M",
    current:
      "The simulation draws each attack type's Poisson count independently. Real campaigns do not work that way — a phishing wave lands credential theft, which lands ransomware.",
    change:
      "A Gaussian or t-copula over the per-type frequency draws, with the correlation matrix estimated from co-occurrence of attack types within the same company_id in the incident base, where several organisations appear more than once.",
    impact:
      "Independence understates the variance of the annual total and therefore both tail metrics — the aggregate is too well-behaved. Calibration raised the value of fixing it: at λ ≈ 0.31 the annual total is dominated by whether an incident happens at all, so correlation between types now shapes the tail materially, where at the old λ ≈ 9,168 the aggregate was so smooth that dependence barely registered.",
  },
];
