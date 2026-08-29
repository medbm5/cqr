# 09 — Severity and simulation views

**Commit:** `feat(web): severity fit and monte carlo results pages`

## Prompt given

> /severity: per attack_type tabs — log-x histogram of weighted peer losses with
> fitted lognormal overlay, fitted params + implied median/mean StatTiles,
> QQ-plot, peer-group panel (weighting rules, effective n).
> /simulation: params (n_years, seed) + Run button → POST /api/simulate/ with
> progress animation; staggered results reveal: AAL as huge animated € counter,
> VaR/TVaR 95/99 tiles, annual-loss histogram, OEP/AEP curves on log-y with
> tooltips ("1-in-20-year loss exceeds €X"); expandable "Why this number" trace;
> 3×3 sensitivity heatmap. Presentation centerpiece — polish the motion.

## Colour job per chart

Reusing the palettes validated in the previous commit; no new palette was needed.

| Chart | Job | Encoding |
|---|---|---|
| Peer-loss histogram + fit | 2 series (evidence vs claim) | categorical slots 1–2, legend present |
| QQ plot | 1 series + a reference | slot 1; the diagonal is a neutral hairline, not a series |
| Annual-loss histogram | 1 series | one hue, no legend box |
| AEP / OEP curves | 2 series, **same units** | slots 1–2 on **one** y-axis |
| 3×3 sensitivity | continuous magnitude | sequential ramp + scale legend + direct labels |

**AEP and OEP share one axis.** Both are losses in euros, so a second y-scale
would invent a relationship the data does not contain — the single most common
charting mistake, and the one the anti-pattern catalog leads with.

## Decisions taken

1. **The progress indicator is indeterminate, and the timer is real.** The engine
   reports no progress, so a percentage would be invented. An indeterminate bar
   plus genuine elapsed seconds says "working, this long so far" without
   claiming to know how much is left.
2. **Running is a button, not a side effect of the controls.** A simulation takes
   seconds; a slider that triggered one on every drag would queue work nobody
   asked for. Changed parameters mark the result stale and re-label the button.
3. **Exactly one hero figure per view.** AAL, at 5–6xl, in the same sans as
   everything else, with proportional digits. A second display number would
   leave the reader with no idea which one the page is about.
4. **Both exceedance axes are logarithmic.** Return period spans 2 to 10,000
   years; on a linear x the entire curve collapses into the left edge. The prompt
   asked for log-y, and log-x is the same argument applied to the other axis.
5. **Every sensitivity cell is direct-labelled** as well as colour-filled. That
   grid is the argument about how robust the headline is, not an illustration of
   it, so no cell may be gated behind a hover.
6. **"Why this number" is collapsed by default.** Twenty-two lines of trace is
   the answer to a question the reader has to ask first; open by default it would
   push the charts below the fold.
7. **A pooled-fallback fit is called out in prose**, not just flagged in a tile.
   "Priced at the pooled rate" is a caveat about the number's meaning, and a
   reader who skims tiles should still meet it.
8. **The QQ diagonal is neutral, not a second series colour.** It is a reference
   line, and colouring it as data would imply the fit has two components.

## One engine addition

`SimulationResult.histogram(bins)` and a `histogram` field on the simulate
response. The annual-loss distribution existed only as the stored per-year
series; the API returned metrics and curves but nothing to draw a distribution
from. Deriving one client-side from the AEP curve would have meant
differentiating an inverse CDF in the browser — arithmetic in the presentation
layer, which is exactly what the architecture forbids.

## Verified against live data

```
/severity    fit histogram · QQ plot · peer-group panel · pooled-fallback notice
             tabs across all nine attack types
/simulation  hero AAL €12.5B · VaR/TVaR tiles · loss histogram · AEP+OEP curves
             9 sensitivity cells · "a factor of 7.2 between the corners"
             "Why this number" trace
```

243 backend tests pass, lint and typecheck clean, all five routes build dynamic.

## A stale server, again

The simulation page 500'd on first check: `histogram` was undefined. The API had
been started before the field existed and runs with `--noreload`, so it was
serving the older contract. Same class of problem as the last commit — a
long-lived dev server silently answering an older API — and the same lesson: when
the frontend reports a missing field, check what the server is actually running
before looking at the client.

## Still not verified visually

Browser tooling remains unavailable. All four chart-bearing pages have been
checked structurally against live data and build clean, but **nobody has looked at
them**. This commit is the one where that matters most: it was asked for as the
presentation centrepiece, and staggered reveals, the counter's easing, label
collisions on the log axes and the sensitivity grid's behaviour on a narrow
viewport are precisely what a structural check cannot see.
