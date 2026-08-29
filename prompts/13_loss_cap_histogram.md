# 13 — Loss plausibility cap and a readable loss histogram

**Commit:** `feat(simulation): plausibility cap on incident losses; readable log-binned loss histogram`

## Prompt given

> The /simulation "Simulated annual loss" histogram is unreadable and revealed a
> modeling flaw. Two changes:
>
> **A) MODELING — loss cap in risk_engine/simulation:** Add parameter
> `loss_cap_eur` (default: 99.9th percentile of the cleaned peer losses,
> ~€30-50M; expose in `POST /api/simulate/`). Every sampled incident loss is
> `min(draw, cap)`. Rationale in docstring: an unbounded lognormal with σ≈2.6
> draws single losses exceeding 10x the company's plausible revenue; losses are
> physically bounded by what the company can lose. Report in the result how many
> draws were capped and the AAL with/without cap so the effect is visible, and
> add it to `to_explanation()`. Add a test: with cap C, no annual loss component
> exceeds C per incident. Re-report AAL/VaR/TVaR (seed 42, 100k years) — expect
> AAL to drop several % and TVaR99 to drop substantially.
>
> **B) CHART — make the histogram readable:** split zero-years out as a labeled
> block; log-scale x bins (40 log-spaced, €1K to max) with ticks at €10K / €100K
> / €1M / €10M / €100M; overlay reference lines for AAL, VaR95, VaR99; keep
> "Show table" in the same log bins; subtitle "Loss years only (27.1% of years);
> zero years shown separately."

## Results, seed 42, 100,000 years

The cap defaults to **€23,476,094** — the 99.9th percentile of the 1,598 cleaned
peer losses. Slightly under the €30–50M the prompt estimated; the rule was
followed rather than the estimate.

| | uncapped | capped | change |
|---|---:|---:|---:|
| AAL | 438,038 | **273,704** | **−37.5%** |
| median year | 0 | 0 | — |
| VaR 95 | 816,323 | 816,323 | **0.0%** |
| TVaR 95 | 8,107,499 | 4,820,816 | −40.5% |
| VaR 99 | 6,665,810 | 6,665,810 | **0.0%** |
| TVaR 99 | 31,567,672 | **15,134,257** | **−52.1%** |
| worst simulated year | **3,841,399,843** | 43,066,333 | −98.9% |
| P(no loss) | 73.71% | 73.71% | — |

**The AAL effect is far larger than the prompt anticipated** — 37.5%, not "several
%". 273 of 30,443 drawn incidents (0.897%) hit the ceiling, and that 0.9% of
draws carried 37.5% of the average annual loss. That concentration is itself the
argument for the cap.

**VaR is completely unchanged and TVaR halves.** Both are correct and worth
stating: a per-incident ceiling of €23.5M cannot move the 95th or 99th
percentile of *annual* loss, because those sit at €0.8M and €6.7M — far below it.
It only touches the mean and the tail averages, which are exactly the statistics
a single implausible draw distorts.

**The uncapped worst year was €3.84 billion** for a 1,200-employee ETI. That
figure is the clearest statement of the flaw: the lognormal was extrapolating
roughly two orders of magnitude past its largest observation (€31.6M).

Also: `data_breach`'s share of the AAL falls from 61% to 46%, because the cap
bites hardest on the widest distribution.

## Decisions taken

**σ figures corrected.** The prompt's rationale cited σ≈2.6. The fitted values
are 1.99 pooled, 2.41 data breach, 2.58 supply chain, down to 1.37 phishing. The
docstrings quote the real range rather than the estimate.

**Unweighted quantile.** `SeverityModel.loss_quantile()` reads the empirical,
*unweighted* distribution of cleaned losses. Everything else in the severity
module is peer-weighted, because there the question is "what does an incident
cost an organisation like this one". Here the question is how large a single
loss is physically possible, which is a property of the observed population, not
of which members resemble the target — weighting it would let a thin peer group
shrink the bound on similarity rather than on evidence. Documented at the method.

**The cap binds per incident, not per year.** A year with three capped incidents
costs three caps. Only the single implausible loss is disallowed, not the
accumulation of plausible ones. The invariant test therefore asserts against
`annual_maxima` (the largest single draw in any year), not against annual totals.

**`aal_uncapped` is a running scalar, not a second per-year array.** The
comparison a reader needs is of averages, and a second `n_years` array would cost
memory the block budget exists to protect.

**A point mass at the cap is visible and is labelled.** Every year holding one
capped incident costs exactly €23.5M, so one histogram bin carries a spike (322
years against ~150 in its neighbours). Unlabelled it reads as a bug, so the chart
draws a fourth reference line at the cap and the caption says what it is.
Truncating the distribution at fitting time instead of clipping the draws would
avoid the point mass — noted in `next_steps.md` item 3b.

## Chart

All five requirements are met, with two additions:

- Zero-years are lifted out into a labeled block above the plot: "73.7% of years
  cost €0 — 73,710 of 100,000 simulated years, no incident occurred".
- Bins are log-spaced by the **engine**, not the client: `histogram(scale="log")`
  returns edges, `zero_years`, `loss_years` and `below_floor_years`. Putting the
  binning in the client would let a second consumer bin it differently and
  disagree with the API about the same run.
- Bars use the geometric midpoint of each bin, not the arithmetic one — on a log
  axis the arithmetic centre sits visibly right of the bin it belongs to.
- **Added:** a reference line at the cap (see above).
- **Added:** the table twin carries a `€0 — no incident at all` row. Dropping it
  would make the shares silently not sum, and the table is the accessible
  reading of the chart, not a subset of it.
- 161 of 26,290 loss-years fall below the €1K floor. They are clipped into the
  first bin rather than dropped, and counted in `below_floor_years`, so the bars
  always sum to `loss_years`.

## Tests

Backend 272 (was 255). New: the per-incident invariant under an explicit cap;
default cap read off the observed quantile; caller-supplied cap records no
quantile; the cap lowers AAL and reports the reduction; `math.inf` runs
genuinely uncapped; a non-binding cap is bit-identical to uncapped; the cap
reaches the trace; non-positive cap refused. Histogram: bins plus zero-years
account for the run; zero-years are separated; log edges are geometric and
linear edges arithmetic; sub-floor years fold into the first bin; a run with no
losses yields empty edges rather than invented ones; unknown scale refused. API:
explicit cap accepted, default quantile reported, non-positive rejected, and the
cap is part of the `lru_cache` key — two caps are two answers.

## Concept with no glossary entry

Per the standing rule from annex 12, reported rather than written: **the loss
cap** now appears on `/simulation` (hero note, chart reference line, caption)
and has no `GLOSSARY` entry. It wants one — it is a modeling assumption
responsible for 37.5% of the headline figure.
