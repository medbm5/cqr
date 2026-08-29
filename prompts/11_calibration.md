# 11 — Frequency calibration

**Commit:** `fix(frequency): calibrate detected attacks into loss incidents`

## Prompt given

> The real issue is a category mismatch: λ counts detected attack episodes, but
> the severity model prices loss-generating incidents. Those are different units.
> Verified anchor: 1,310 companies over ~4 years → 0.31 incidents/company/year.
> 1. Proceed with asset-only clustering. 2. Add a calibration stage:
> λ_incident = λ_detected × p_materialize, fitted against the peer-weighted base
> rate; keep the attack-type MIX from telemetry. 3. Rename honestly. 4. Replace
> the λ < 1000 guard with 0.05 < λ_incident < 5. 5. Simulation consumes
> λ_incident. 6. Document p_materialize in next_steps.

## The diagnosis, honestly

Three bugs were suspected. **Two were not real**, and I said so rather than
finding something to fix:

- **Severity filter** — already applied *before* bucketing (`episodes.py:136`).
- **Gap logic** — already rolling against the previous event on a pre-sorted
  bucket (`episodes.py:142-145`); the 220-hour maximum episode proved chaining
  worked.
- **Clustering key** — real, but it was a decision approved in feature 3, not a
  defect. I had put that exact fork with measured numbers (911 episodes vs 5,198)
  and it was chosen the other way. Reversing it is a modeling decision, and it was
  right to reverse.

The deeper problem was neither: **λ and the severity model were in different
units.** Detected attacks were being priced as though each were a breach.

## Numbers

| | before | after |
|---|---|---|
| episodes | 5,325 | **911** |
| compression (attack-grade per episode) | 1.90x | **11.09x** |
| λ detected | 9,168/yr | 1,568.5/yr |
| λ incident | — | **0.3052/yr** |
| AAL | €12,471,807,357 | **€438,038** |
| median year | €11,867,291,411 | **€0** |
| P(no loss) | 0.0% | **73.7%** |
| VaR 99 | €22,987,482,942 | €6,665,810 |
| TVaR 99 | €32,388,088,830 | €31,567,672 |

The anchor was verified three ways before being built on: crude 0.306, ETI subset
0.304, peer-weighted **0.3052** incidents per organisation-year.

**The shape came back.** P(no loss) = 73.7% is exactly e^-0.3052. Three years in
four are quiet, the median year costs nothing, TVaR 99 is 72x the AAL. The old
model had a mean within 5% of its median and no loss-free year in 100,000 —
the central limit theorem flattening 9,168 draws a year into a near-Gaussian
aggregate. The bad frequency had not merely inflated the answer, it had destroyed
the distribution's shape.

## Decisions taken

1. **`p_materialize` is fitted, not configured.** It is whatever reconciles this
   estate's detection rate with what comparable organisations actually lose, and
   it is reported rather than set. At 1.95e-4 — one detected attack in 5,100 — it
   reads as a diagnostic: the sensors are noisy, not the company safe.
2. **The base rate weights numerator *and* denominator.** Incidents count in
   proportion to peer similarity, and so do organisation-years. Weighting only the
   numerator would divide peer incidents by every organisation in the base and
   understate the rate.
3. **A mixed episode is labelled by its worst event**, ties to the earliest. Asset-
   only clustering means an episode spans several attack types; the worst detection
   is the best guess at what the intrusion was.
4. **Zero detected attacks is an answer, not a missing calibration.** The simulation
   distinguishes "uncalibrated" (raises) from "nothing was detected" (AAL 0).
5. **Calibration lives in `frequency/` and imports `severity.peers`**, as directed.
   It inverts the stage order slightly; the alternative was duplicating the kernel,
   which would have let the two halves drift apart.

## Flagged, not tuned

- **AAL is €438k, not the €174k a `0.3 × pooled mean` check predicts.** The mix
  matters: `data_breach` carries 19.2% of episodes against 12.6% of the base's
  incidents, and its fitted mean is €4.78M, so it contributes **61%** of the AAL.
  Keeping the telemetry's mix — as specified — is what moves it.
- **The sensitivity grid collapsed from 7.2x to 1.41x.** λ_incident reads 0.3052 in
  all nine cells: the threshold and window now only reshuffle the mix. The telemetry
  no longer influences how often losses happen at all.
- **Episode counts are not monotone in the threshold.** `critical` yields *more*
  episodes (1,062) than `medium` (741), because looser thresholds admit more events
  that chain into longer episodes. An API test asserting the opposite was rewritten.
- **The worst simulated year is €3.84bn**, from `data_breach`'s σ=2.41 lognormal —
  and the Pareto diagnostic says that tail is understated.

## Tests

`backend/tests/test_frequency.py`, 11 regression tests covering all five specified
cases: the 3-day chain of daily events collapsing to one episode, three techniques
in an hour collapsing to one, low/medium excluded before clustering, the 24h /
24h+1s boundary pair, and the plausibility band `0.05 < λ_incident < 5` on the real
data. 254 tests pass overall.
