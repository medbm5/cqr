# 04 — Severity model

**Commit:** `feat(severity): loss distribution fitted on comparable incidents`

## Prompt given

> Build backend/risk_engine/severity/ from data/cyber_incidents.csv.
> - Cleaning: mojibake replacement dict for sector, financial_loss_eur <= 0
>   flagged missing (never €0), parsed dates; return CleaningReport with per-rule
>   counts.
> - Peer weighting (soft, not hard filter): weight = w_sector(Retail=1 else 0.4) ×
>   w_size(ETI=1 else 0.6) × gaussian kernel on |maturity−55|; all weights
>   parameterized; report effective sample size (Kish).
> - Weighted lognormal MLE per attack_type on log-losses; diagnostics vs empirical
>   + a Pareto-tail candidate (QQ data, weighted KS); fallback to pooled
>   distribution when effective n < 30 (reported).
> - Output SeverityModel: sample(attack_type, n, rng), params_by_type,
>   fit_diagnostics, to_explanation() (sample sizes, weights, fitted μ/σ with
>   implied median/mean in €).
> Deterministic under seed. Tests: cleaning rules, weighting math, parameter
> recovery on synthetic lognormal, fallback trigger.

## Result on the case data

```
pooled: n_eff 1,077.5 of 1,598   mu=11.267 sigma=1.994  median EUR 78,230  mean EUR 571,339

credential_theft  n= 222  n_eff= 147.7   median EUR 103,378   mean EUR   875,306
data_breach       n= 201  n_eff= 130.5   median EUR 262,325   mean EUR 4,782,253
ddos              n= 139  n_eff=  94.0   median EUR  45,615   mean EUR   159,020
insider_error     n= 129  n_eff=  86.4   median EUR  44,074   mean EUR   118,737
misconfiguration  n= 182  n_eff= 125.4   median EUR  43,802   mean EUR   136,439
phishing          n= 371  n_eff= 247.6   median EUR  35,326   mean EUR    90,503
ransomware        n= 276  n_eff= 195.1   median EUR 147,086   mean EUR 1,191,022
supply_chain      n=  78  n_eff=  52.3   median EUR 183,256   mean EUR 5,131,124
other             n=   0  n_eff=   0.0   [no incidents of this type -> pooled]
```

**Soft weighting does what it was chosen for.** Hard filtering to exact peers
leaves 112 incidents and zero usable per-type cells (notebook section 8). Under
soft weighting every one of the eight named types clears n_eff = 30 on its own
data, and the fallback fires only for `other`, which has no incidents at all.

166 tests, 100% coverage of the severity package.

## Decisions taken (flagged for validation)

1. **The mojibake table is explicit, and a test proves it correct.** The prompt
   asked for a replacement dict; notebook section 6 argued for a cp1252/UTF-8
   round-trip because a table can miss a label it has never seen. Both are
   honoured: `SECTOR_MOJIBAKE` is what the pipeline applies, so a reviewer can
   see every change without running anything, and `repair_mojibake` is kept as
   the reference transformation with a test asserting the table reproduces it
   exactly. The table cannot drift from the rule it claims to encode.
2. **`maturity_bandwidth` defaults to 15.** The prompt specified a Gaussian
   kernel but not its width, and the width is what decides how sharp the peer
   group is. Maturity in the base has a standard deviation of about 12, so 15
   keeps most of the base contributing while still favouring organisations
   defended about as well as the target. This is the one free parameter in the
   weighting and the first thing to vary in a sensitivity check.
3. **`AttackType` moved to `risk_engine/attack_types.py`.** It is now needed by
   two stages, and having severity import it from `risk_engine.frequency` would
   have implied a dependency that does not exist. The technique mapping stays in
   frequency, which is where it belongs. `risk_engine.frequency` still re-exports
   the enum, so nothing downstream changed.
4. **`sigma` is the maximum-likelihood estimate, uncorrected for bias.** It is
   what the simulation stage needs in order to reproduce the fitted distribution,
   and with effective sample sizes in the hundreds the correction is far below
   the uncertainty in the inputs.
5. **The weighted KS statistic is reported without a p-value.** The usual tables
   assume equal weights and known parameters; neither holds here. Reporting a
   p-value would dress a comparable magnitude up as a hypothesis test.
6. **A fit's `diagnostics` may belong to the pooled distribution.** When a type
   has no incidents at all there is nothing of its own to diagnose. The type's
   real sample is therefore carried separately as `own_observations` /
   `own_effective_n` — without that split the trace showed `other n=1,598`, which
   read as 1,598 incidents of an attack type that has none.

## Flagged for validation

**The Pareto rival beats the lognormal on five of the eight tails**, and on two
of them with `alpha < 1`:

| type | alpha | verdict |
|---|---|---|
| misconfiguration | 0.59 | Pareto fits the tail better |
| phishing | 0.87 | Pareto fits the tail better |
| other / pooled | 1.11 | Pareto fits the tail better |
| ransomware | 1.51 | Pareto fits the tail better |
| credential_theft | 1.72 | Pareto fits the tail better |

An `alpha` below 1 implies an infinite theoretical mean. Read literally that is
an artefact of a small exceedance sample, not a claim about the world — but the
direction is consistent and it means **the lognormal understates the extreme
losses that VaR and TVaR are made of**. AAL, driven by the body, is far less
affected. The diagnostic exists to make this visible rather than to act on it
automatically; whether the simulation stage should use a spliced
lognormal-body/Pareto-tail severity is a modeling decision worth taking
deliberately.

**Three tails could not be tested at all** — data_breach, ddos and supply_chain
had fewer than `min_exceedances = 15` observations above the weighted 90th
percentile. data_breach has the second-largest mean of any type, so its tail is
exactly the one worth testing. Lowering `tail_fraction` or `min_exceedances`
would produce a verdict on a noisier sample; neither was changed silently.

**A property of Kish worth knowing before reading the n_eff column:** effective
sample size measures how *evenly* weight is spread, not how large it is. Forty
peers all discounted to 0.24 still count as forty. What collapses n_eff is one
close peer among many distant ones. Both halves of this are covered by tests,
because it is easy to misread the fallback as broken when it does not fire on a
uniformly distant group.
