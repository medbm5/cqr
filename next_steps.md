# Next steps

Ideas that came up during the work and were deliberately not built. Each is
listed with what it would fix, roughly what it would cost, and — where it
matters — why it was *not* the next thing to do.

The list is ordered by what would most change the answer, not by what would be
most interesting to write.

---

## 1. Gamma-Poisson credibility: blend telemetry with base rates

**The problem it fixes.** The single biggest defect in this deliverable. The
telemetry implies λ ≈ 9,168 attacks/year on a 20-asset estate, which is not a
plausible rate for any real company. The engine currently trusts the telemetry
completely, because it has nothing else to trust.

**What it would look like.** Treat the per-attack-type rate as
`λ ~ Gamma(α, β)` with the prior set from the incident base — the observed
frequency of each attack type across ~1,600 incidents at comparable
organisations, scaled to a company of this size — and the likelihood from the
telemetry episodes. The posterior mean is then a credibility-weighted blend:

```
λ_posterior = Z · λ_telemetry + (1 − Z) · λ_prior,   Z = n / (n + k)
```

with `Z` rising as the observation window lengthens. Seven months of telemetry
would carry real but not total weight, and the estimate would stop being
hostage to one estate's detection verbosity.

**Why it wasn't done.** It is a genuine modeling addition rather than a
refinement, and it needs a defensible prior — deriving incident *rates* from an
incident *base* means assuming an exposure denominator the data does not
contain. Doing it badly would replace an obviously wrong number with a
plausible-looking wrong number, which is worse. This is the first thing I would
build next.

---

## 2. GPD tail via peaks-over-threshold

**The problem it fixes.** The severity stage already reports that a Pareto tail
describes the extremes better than the fitted lognormal on **five of eight**
attack types, twice with α < 1. VaR 99 and TVaR 99 are made almost entirely of
that tail, so they are currently understated by an unknown margin.

**What it would look like.** A spliced severity distribution: lognormal body
below a threshold `u`, generalised Pareto above it, fitted by maximum likelihood
on the exceedances, with `u` chosen from a mean-residual-life plot rather than a
fixed quantile. `sample()` would draw from the mixture.

**Why it wasn't done.** Three of the eight types have fewer than 15 exceedances
above the weighted 90th percentile — including `data_breach`, which has the
second-largest mean and therefore the tail most worth modelling. Fitting a GPD to
a dozen points produces a shape parameter with enormous variance. The honest move
was to report the diagnostic and leave the fit alone; the code already carries
`ParetoTail` with a Hill estimate, so the evidence is in the output rather than
in my head.

---

## 3. Dependence between attack types (copulas)

**The problem it fixes.** The simulation draws each attack type's Poisson count
independently. Real campaigns do not work that way: a phishing wave lands
credential theft, which lands ransomware. Independence understates the variance
of the annual total and therefore both tail metrics — the aggregate is too
well-behaved.

**What it would look like.** A Gaussian or t-copula over the per-type frequency
draws, with the correlation matrix estimated from co-occurrence of attack types
within the same `company_id` in the incident base — several organisations appear
more than once, which is exactly the signal needed.

**Why it wasn't done.** At λ ≈ 9,168 the aggregate is already nearly
deterministic, so correlation would barely move the current number. This becomes
worth doing *after* item 1, not before — it is a refinement to a frequency that
is currently wrong by orders of magnitude.

---

## 4. Control effectiveness and a FAIR-style maturity adjustment

**The problem it fixes.** Maturity 55/100 currently affects only *which peers are
weighted*, through the Gaussian kernel. It does not affect the company's own
frequency or severity at all — so improving the security programme would not move
the modelled loss, which is the wrong incentive for a tool meant to justify
security spend.

**What it would look like.** Split the FAIR chain properly: threat event
frequency (what arrives) × vulnerability (what gets through, a function of
maturity) = loss event frequency, and a maturity-dependent scaling on severity
for containment. Calibrate the maturity → vulnerability curve by regressing loss
on `security_maturity_score` in the incident base, controlling for size and
sector.

**Why it wasn't done.** Scope, and a real risk of double-counting: the telemetry
already reflects this company's controls, since a well-defended estate generates
different detections. Applying a maturity discount on top would deflate twice.
Getting this right needs care about what each data source already encodes.

---

## 5. Asset-level loss allocation by criticality

**The problem it fixes.** The output is one number for the whole company. The
question a CISO actually asks is "which assets carry it", and the engine already
knows episodes per asset — it just never carries that through to euros.

**What it would look like.** Allocate each simulated incident to the asset whose
episode generated it, then scale severity by a criticality multiplier so a
criticality-5 database costs more than a criticality-1 workstation. The output
becomes a ranked list of assets by expected annual loss, which is directly
actionable.

**Why it wasn't done.** The multiplier would be invented. Nothing in the incident
base ties loss to asset criticality — it records company-level losses, not
per-asset ones — so any curve would be my assumption wearing a number's clothes.
Notebook §5 found severity is statistically independent of criticality in the
telemetry (26–27% attack-grade at every level), so the data actively declines to
supply this. It needs an external source or an explicit, labelled assumption.

---

## 6. Backtesting against the incident base

**The problem it fixes.** Nothing currently validates the model's output against
observed reality. Every check in the suite is internal consistency.

**What it would look like.** Hold out a slice of `cyber_incidents.csv` — say the
most recent year — fit on the rest, and score the predicted loss distribution
against the held-out losses with a proper scoring rule (CRPS) or a PIT histogram.
For frequency, split the telemetry window in half and check that the rate
estimated on the first half predicts the second.

**Why it wasn't done.** The frequency half is cheap and I would do it first. The
severity half is harder than it looks: the model predicts losses *for this
company*, and the held-out incidents are other companies, so a naive backtest
scores the peer weighting rather than the fit. Doing it properly means
cross-validating the weighting scheme itself — leave-one-company-out, predicting
each held-out organisation's losses from its own peer group.

---

## 7. Threat-intelligence enrichment

**What it would look like.** Join the observed ATT&CK techniques to campaign and
actor data — which actors use T1486, which sectors they target — to adjust
per-type frequency by whether an actor active against Retail is known to use that
technique. This is Citalid's own domain, and it is what would make the technique →
attack-type mapping evidence-based rather than a judgment call.

**Why it wasn't done.** No such feed is in the supplied data. It would be the
highest-value addition if one were available, because it addresses the mapping
flagged as `ARGUABLE` in four places.

---

## 8. CI pipeline

**What it would look like.** GitHub Actions running `make lint test` on push, a
matrix over Python 3.11–3.13, the notebook executed with `nbconvert` to catch
drift between it and the engine, and coverage reported as a check. Pre-commit
already runs ruff and mypy locally; CI is the same gates where they cannot be
skipped.

**Why it wasn't done.** Pure infrastructure, no effect on the answer. The gates
themselves exist and run.

---

## 9. Authentication on the API

**What it would look like.** The API is `AllowAny` and read-only, which is right
for a local case study and wrong for anything else. Token or session auth on the
write path (`POST /api/simulate/`), rate limiting on it since a 200,000-year
request occupies a worker for half a minute, and CORS already reads from the
environment in production settings.

**Why it wasn't done.** Nothing here is sensitive and nothing is deployed. Worth
naming because "the API has no auth" should be a decision on the record, not an
oversight someone discovers later.

---

## Smaller things

- **Per-asset weekly episode data is computed but barely used** — the heatmap
  shows it; a per-asset drilldown would use it properly.
- **`results.json` has no schema.** It is consumed by nothing but a human today,
  but if the frontend ever read it directly it would want one.
- **The notebook re-derives constants the engine also computes.** They agree
  today, and a test asserting the notebook's headline figures against the engine
  would keep them agreeing.
- **No caching of the simulation across processes.** `lru_cache` is per-worker,
  so a multi-worker gunicorn deployment recomputes per worker. Redis would fix it
  if this were ever deployed.
