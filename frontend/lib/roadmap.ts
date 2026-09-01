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
    id: "p-materialize-sensitivity",
    title: "Report the answer's sensitivity to p_materialize",
    phase: 1,
    theme: "modeling",
    effort: "S",
    current:
      "p_materialize is a single fitted scalar — 1.95e-4 on this data, one detected attack in 5,100 becoming a loss — and it appears only as a line in the explanation trace.",
    change:
      "Sweep it the way the severity threshold and session window are already swept, and surface the result beside the existing 3×3 sensitivity grid.",
    impact:
      "It is the single most influential number in the pipeline and currently the least visible. A reader could see how much of the headline rests on it instead of taking it on trust. This is the cheapest item on the list and the one with the best ratio of effort to honesty.",
  },
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
  {
    id: "asset-drilldown",
    title: "Per-asset drilldown",
    phase: 2,
    theme: "platform",
    effort: "S",
    current:
      "Per-asset weekly episode data is computed on every request and used for exactly one thing — the heatmap.",
    change:
      "A per-asset view built on the data already in the response: episode history, severity mix and attack-type profile for one machine.",
    impact:
      "A presentation change rather than a modeling one, but it answers the question the heatmap raises and cannot resolve — which asset is that dark row, and what happened on it. Note this is *not* asset-level loss allocation, which needs a criticality multiplier the data does not support (phase 3).",
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
    id: "maturity-p-materialize",
    title: "Model p_materialize instead of fitting one scalar",
    phase: 3,
    theme: "modeling",
    effort: "L",
    current:
      "One fitted number converts detected attacks into loss-generating incidents. It absorbs, in a single scalar, how noisy the sensors are, how good the controls are and how fast the response is.",
    change:
      "Split it the way FAIR does — p_materialize = p_control_failure(maturity) × p_impact_given_failure(asset, attack_type) — with the maturity term calibrated by regressing incident frequency on security_maturity_score across the base, controlling for size and sector.",
    impact:
      "A company at maturity 75 would show a genuinely lower incident rate than one at 35, which the current construction cannot express: both inherit the same peer-weighted anchor. It was not done because the regression needs an exposure denominator the base does not contain — it records incidents, not organisation-years at risk — so a low-maturity company appearing three times might be badly defended or simply unlucky. The single scalar is the honest version: visibly one number doing one job, rather than a model implying knowledge that is not there.",
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
    id: "exposure-cap",
    title: "Derive the loss cap from the company's own exposure",
    phase: 3,
    theme: "modeling",
    effort: "M",
    current:
      "Every drawn incident is clipped at the 99.9th percentile of the cleaned peer losses (€23,476,094) — real evidence, but a property of the peer population rather than of this company.",
    change:
      "A per-company exposure ceiling built from figures an engagement would already have — annual revenue, balance-sheet assets, the record count behind a GDPR exposure, contractual liability caps — and truncation of the severity distribution at fitting time rather than clipping of the draws at simulation time.",
    impact:
      "A 1,200-employee retailer and a 4,000-employee manufacturer currently sit under the same ceiling, which cannot be right: what an organisation can lose is a function of what it has. The assumption is not a small one — the cap removes 37.5% of the AAL and 52% of TVaR 99. Truncating rather than clipping is also statistically cleaner: it removes the point mass the current cap leaves at the ceiling, visible as a spike in the loss histogram. It was not done because the case data carries no financial profile for the target company at all.",
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
  {
    id: "control-effectiveness",
    title: "Control effectiveness and a FAIR-style maturity adjustment",
    phase: 3,
    theme: "modeling",
    effort: "L",
    current:
      "Maturity 55/100 affects only which peers are weighted, through the Gaussian kernel. It does not touch this company's own frequency or severity at all.",
    change:
      "Split the FAIR chain properly: threat event frequency (what arrives) × vulnerability (what gets through, a function of maturity) = loss event frequency, plus a maturity-dependent scaling on severity for containment.",
    impact:
      "Improving the security programme currently does not move the modelled loss, which is the wrong incentive for a tool meant to justify security spend. The risk to manage is double-counting: the telemetry already reflects this company's controls, since a well-defended estate generates different detections, so a maturity discount applied on top would deflate twice. Getting it right needs care about what each data source already encodes.",
  },
  {
    id: "asset-allocation",
    title: "Asset-level loss allocation by criticality",
    phase: 3,
    theme: "modeling",
    effort: "M",
    current:
      "The output is one number for the whole company. The engine already knows episodes per asset — it just never carries that through to euros.",
    change:
      "Allocate each simulated incident to the asset whose episode generated it, then scale severity by a criticality multiplier, so a criticality-5 database costs more than a criticality-1 workstation.",
    impact:
      "The output becomes a ranked list of assets by expected annual loss, which is directly actionable and is the question a CISO actually asks. It was not done because the multiplier would be invented: the incident base records company-level losses, not per-asset ones, and the notebook found severity statistically independent of criticality in the telemetry — 26–27% attack-grade at every level. The data actively declines to supply this, so it needs an external source or an explicit, labelled assumption.",
  },
  {
    id: "threat-intel",
    title: "Threat-intelligence enrichment",
    phase: 3,
    theme: "data",
    effort: "L",
    current:
      "The technique → attack-type mapping is a judgment call, with four attributions marked ARGUABLE in the source alongside their alternative and their event weight.",
    change:
      "Join the observed ATT&CK techniques to campaign and actor data — which actors use T1486, which sectors they target — and adjust per-type frequency by whether an actor active against Retail is known to use that technique.",
    impact:
      "It would make the mapping evidence-based rather than a judgment call, addressing the four attributions currently flagged as arguable. This is Citalid's own domain, and it would be the highest-value addition of anything on this page — but no such feed exists in the supplied data.",
  },
];
