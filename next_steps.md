# Next steps

Ideas that came up during the work and were deliberately not built. Each is
listed with what it would fix, roughly what it would cost, and — where it
matters — why it was *not* the next thing to do.

The list is ordered by what would most change the answer, not by what would be
most interesting to write.

---

---

## 1. Gamma-Poisson credibility: blend telemetry with base rates

**The problem it fixes.** The engine no longer trusts the telemetry's magnitude
at all — it anchors the incident rate entirely on the peer base (0.3052 per
organisation-year) and lets the telemetry supply only the attack-type mix. That
is safe, but it is the opposite extreme: seven months of this company's own
telemetry now carries **zero** weight in how often losses happen. An estate that
genuinely is attacked twice as often as its peers would be priced identically to
one that is not.

**What it would look like.** Treat the per-attack-type rate as
`λ ~ Gamma(α, β)` with the prior set from the incident base — the observed
frequency of each attack type across ~1,600 incidents at comparable
organisations, scaled to a company of this size — and the likelihood from the
telemetry episodes. The posterior mean is then a credibility-weighted blend:

```
λ_posterior = Z · λ_telemetry + (1 − Z) · λ_prior,   Z = n / (n + k)
```

with `Z` rising as the observation window lengthens. Seven months of telemetry
would then carry real but not total weight — a middle ground between the old
model, which trusted it completely, and the current one, which does not trust it
at all.

**Why it wasn't done.** The blend needs a credible `k` — how many
organisation-years of telemetry are worth one organisation-year of base rate —
and nothing in the data pins it. Choosing one by feel would quietly decide how
much this company's own evidence counts, which is exactly the judgment the
credibility framework exists to make explicit. This is still the first thing I
would build next.

---

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

**Why it wasn't done.** Scope. Note that calibration *raised* its value: at
λ_incident ≈ 0.31 the annual total is dominated by whether an incident happens at
all, so correlation between types now shapes the tail materially — where at the
old λ ≈ 9,168 the aggregate was so smooth that dependence barely registered.
This has moved up the list.

---

---

## 4. Backtesting against the incident base

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

---

## 5. CI pipeline

**What it would look like.** GitHub Actions running `make lint test` on push, a
matrix over Python 3.11–3.13, the notebook executed with `nbconvert` to catch
drift between it and the engine, and coverage reported as a check. Pre-commit
already runs ruff and mypy locally; CI is the same gates where they cannot be
skipped.

**Why it wasn't done.** Pure infrastructure, no effect on the answer. The gates
themselves exist and run.

---

---

## 6. Authentication on the API

**What it would look like.** The API is `AllowAny` and read-only, which is right
for a local case study and wrong for anything else. Token or session auth on the
write path (`POST /api/simulate/`), rate limiting on it since a 200,000-year
request occupies a worker for half a minute, and CORS already reads from the
environment in production settings.

**Why it wasn't done.** Nothing here is sensitive and nothing is deployed. Worth
naming because "the API has no auth" should be a decision on the record, not an
oversight someone discovers later.

---

---

## Smaller things

- **`results.json` has no schema.** It is consumed by nothing but a human today,
  but if the frontend ever read it directly it would want one.
- **The notebook re-derives constants the engine also computes.** They agree
  today, and a test asserting the notebook's headline figures against the engine
  would keep them agreeing.
- **No caching of the simulation across processes.** `lru_cache` is per-worker,
  so a multi-worker gunicorn deployment recomputes per worker. Redis would fix it
  if this were ever deployed.
