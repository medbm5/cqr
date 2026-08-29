# 05 — Monte Carlo simulation

**Commit:** `feat(simulation): monte carlo annual loss with AAL/VaR/TVaR and exceedance curves`

## Prompt given

> Build backend/risk_engine/simulation/.
> - simulate(frequency, severity, n_years=100_000, seed): per year, Poisson(λ_type)
>   counts per attack_type, loss draws per incident, sum → annual loss. Vectorized
>   numpy (no per-year Python loop), memory-conscious.
> - Metrics: AAL, median, VaR95/99, TVaR95/99, P(loss=0), max.
> - OEP and AEP exceedance curves as plottable arrays (define both in docstrings).
> - Sensitivity: AAL over a 3×3 grid of severity-threshold × session-window.
> - SimulationResult.to_explanation(): full chain (λ per type, severity params,
>   n_years, seed, metrics).
> - CLI: python -m risk_engine --data-dir data/ --out results.json running the full
>   pipeline.
> Tests: analytic case Poisson λ=2 × constant loss 100 → AAL≈200; seed
> reproducibility; TVaR ≥ VaR invariant.

## Result on the case data

```
100,000 simulated years, seed 42, 33 seconds end to end

AAL (mean)          EUR     12,471,807,357
median year         EUR     11,867,291,411
VaR 95              EUR     16,790,073,786
TVaR 95             EUR     21,502,831,858
VaR 99              EUR     22,987,482,942
TVaR 99             EUR     32,388,088,830
worst simulated yr  EUR    200,575,998,547
years with no loss               0.00%

data_breach 65.2% of AAL, ransomware 18.2%, credential_theft 11.4%
```

206 tests, 100% coverage of the simulation package.

## Decisions taken

1. **Blocked vectorization, not a per-year loop.** At λ = 9,168 a hundred thousand
   years is 917 million individual loss draws — 7 GB in one array. Years are
   processed in blocks sized so about `DRAWS_PER_BLOCK` draws are live at once:
   one Poisson draw per attack type per block, one lognormal draw for every
   incident in it, one `bincount` to fold incidents back into years. The loop is
   over a handful of blocks, never over years.
2. **Block boundaries are derived from the arguments alone**, never from
   available memory, so `draws_per_block` changes speed and footprint but not the
   result. A run on a laptop and a run on a server produce identical years from
   the same seed. Tested explicitly.
3. **OEP is computed from a per-year maximum**, tracked alongside the per-year
   total via `np.maximum.reduceat` over the year segments. Empty years are
   excluded from the reduction — `reduceat` would otherwise read past an empty
   segment and report a neighbouring year's loss.
4. **Curve probabilities finer than `1 / n_years` are dropped**, not reported. A
   50-year run has nothing to say about a 1-in-10,000-year loss, and emitting a
   number there would invent precision the run does not have.
5. **The sensitivity grid runs at 10,000 years per cell**, not 100,000. It answers
   a question about the mean, which converges long before the tail does; nine
   full-length cells would cost nine full simulations to say the same thing.
6. **`--sensitivity-years 0` skips the grid**, for a fast headline-only run.

## Flagged for validation — read this before quoting any figure

**The AAL is €12.5 billion a year for a 1,200-employee ETI.** The engine is
arithmetically right and the number is indefensible. It follows directly from the
λ ≈ 9,168 attacks/year flagged in `prompts/03_frequency.md`: the synthetic feeds
grade 31.5% of all events high or critical, so the estate appears to suffer
25 successful attacks a day. Compounding that with a mean severity of about
€1.36M gives what it gives.

**A second, subtler consequence.** At this rate the annual total is nearly
deterministic — the AAL is only **1.1× the median year**, no year in 100,000 is
loss-free, and VaR 99 is under 2× the AAL. That is the central limit theorem
flattening 9,168 draws a year into a near-Gaussian aggregate. It destroys the
shape the exercise exists to show: with a realistic λ of 1–10, most years would
be loss-free, the median would sit far below the mean, and the exceedance curves
would bend sharply. **The implausible frequency does not merely inflate the
answer, it removes its structure.** Anyone reading the curves should know that.

**What the sensitivity grid says about it:**

```
threshold  window    episodes   lambda/yr              AAL
medium        8h      12,639    21,760.5 EUR   26,320,088,014
medium       24h       7,141    12,294.6 EUR   14,372,512,876
medium       72h       2,443     4,206.1 EUR    4,496,625,335
high          8h       7,994    13,763.3 EUR   19,893,695,389
high         24h       5,325     9,168.0 EUR   12,497,020,548  <- baseline
high         72h       2,332     4,015.0 EUR    4,580,423,969
critical      8h       2,326     4,004.7 EUR    7,431,557,829
critical     24h       1,908     3,285.0 EUR    6,059,778,576
critical     72h       1,245     2,143.5 EUR    3,667,014,856
```

A factor of **7.2** between the loosest and strictest defensible settings — and
even the strictest lands at €3.7bn. **No setting in this grid rescues the
figure**, which is the honest conclusion: the problem is the input data's
severity distribution, not the parameter choice. Presenting the grid alongside
the headline number is the point; presenting the headline number alone would be
misleading.

Also still open from feature 4: the Pareto rival beats the lognormal on five of
eight tails. That understates VaR and TVaR specifically, and is not addressed
here.
