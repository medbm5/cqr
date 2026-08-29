# 14 — Exceedance curves rendering on log axes

**Commit:** `fix(web): exceedance curves render on log axes; annotate zero-loss region and tie curves to VaR tiles`

## Prompt given

> The /simulation "Exceedance curves" chart renders no lines. Diagnose first:
> log the series passed to recharts — I expect the short-return-period points
> have loss = 0 (median year is €0), and a log y-axis cannot plot 0, which kills
> the whole line.
>
> Fix: (1) drop points with loss ≤ 0 from BOTH series before plotting; each
> curve starts at its first nonzero return period — for AEP that's around the
> ~1-in-1.4-year mark (27% loss years). (2) Y domain from ~€10K (or first
> plotted value, whichever lower) to max; ticks €10K/€100K/€1M/€10M. X stays log
> return-period with the existing ticks. (3) Annotate the zero region instead of
> hiding it. (4) Fix the tooltip; never €0 rows. (5) Reference dots at
> (20, VaR95) and (100, VaR99) on the AEP curve, labeled. (6) Component test:
> series contain no nonpositive values; AEP ≥ OEP at every shared return period.

## Diagnosis

The hypothesis was right. **10 of 160 points on both curves are exactly €0**,
covering return periods 2.00 → 3.69 years.

```
 idx   return_period      AEP            OEP
    0        2.0000               0              0
    ...
    9        3.6899               0              0
   10        3.9497           3,418          3,417     <- first nonzero
  159   100000.0000      37,142,208     23,476,094
```

`scale="log"` maps 0 to −∞; recharts writes that into the `d` attribute as
`NaN`, and a path with a NaN command is discarded **in its entirety** by the
renderer. Both lines vanished, axes and legend still drew, and nothing threw —
which is why it looked like a styling problem rather than a data one.

A second, compounding fault: `domain={["auto", "auto"]}` on a log y-axis
resolves through the data minimum, so the axis itself was computed from a zero.

**One correction to the prompt's expectation.** The first nonzero point is at a
**~3.9-year** return period, not ~1.4. Two reasons: the curve is evaluated on
log-spaced probabilities starting at p = 0.5, so it never reaches a return period
below 2 at all; and with 26.3% of years carrying a loss, the loss quantile
crosses zero at p = 0.263, i.e. 1/0.263 ≈ 3.8 years. A 1.4-year return period is
p = 0.71 — well inside the zero band. The footnote computes the figure from the
data rather than quoting either number.

## What changed

`buildExceedanceSeries()` was extracted into `exceedance-series.ts` as a pure
function, which is what makes requirement 6 testable without a DOM.

**Null, not omission.** Zero points become `null` and keep their return period.
The lines skip them (`connectNulls={false}`), but the x positions survive, so the
band they occupied can still be shaded and labelled rather than trimmed off the
axis. This satisfies "drop from the series before plotting" for every plotting
purpose while keeping requirement 3 possible.

**The two curves are filtered independently.** They reach zero at the same index
on this data, but nothing guarantees it — AEP is a year's total and OEP its
largest single loss — and a run where they part company at the left edge must not
force one to inherit the other's starting point. Tested explicitly.

**Y domain** is `[min(€10K, smallest plotted value), max]`. On this run the
smallest plotted value is €3,417, so the floor gives way rather than clipping the
line. Ticks land at €10K/€100K/€1M/€10M.

**The table twin keeps the zero rows.** They are real readings of the model; the
table is the complete twin of the chart, not a transcription of what fitted on
the axes.

**Tooltip** now builds its rows from the payload and drops any series without a
positive value at the hovered period, so no "€0" row is ever fabricated. Inside
the zero band it says so in words instead.

## Verification against the live API

Rendered with the real 100,000-year response (`ResponsiveContainer` replaced by a
fixed 900×400, since jsdom measures every element as 0×0 and would otherwise make
every assertion pass vacuously against an empty SVG):

```
paths: 2
  s0 len=16315 NaN=false head=M108.07547169811318,369.98118722519...
  s1 len=16229 NaN=false head=M108.07547169811318,370C109.8113207...
ticks-y: €10K | €100K | €1M | €10M
ticks-x: 2 | 5 | 10 | 20 | 50 | 100 | 500 | 1k | 10k
refArea: 1   refDots: 2
footnote: ... Below a ~3.9-year return period the expected year costs €0 —
          73.7% of years are loss-free ...
```

Both lines begin at x = 108.07 — the first plotted point — with the shaded band
to their left.

## Tests

19 new (frontend total 32). `exceedance-series.test.ts` (13) covers requirement
6 directly — no nonpositive value reaches either plotted series, and AEP ≥ OEP at
every shared return period — plus independent filtering, the y-floor giving way,
the y domain never starting at zero, the all-zero run, and the no-zero-band case.

`exceedance-curves.test.tsx` (6) is a real render test: both lines draw, the path
data contains no `NaN` or `Infinity`, the band is shaded and labelled, both VaR
dots are placed, the footnote carries the run's own numbers, and an all-zero run
states the absence instead of drawing nothing.

**The render test was checked against the bug it guards.** Reverting the null
handling and the y domain makes 5 of its 6 tests fail, "draws both lines" among
them — so it detects the original defect rather than merely passing alongside the
fix.
