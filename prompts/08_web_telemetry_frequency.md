# 08 — Telemetry and frequency views

**Commit:** `feat(web): telemetry pipeline and frequency pages`

## Prompt given

> /telemetry: animated funnel (SIEM 26.5k + EDR 19.4k → merged unique →
> attack-grade) with staggered reveal; weekly stacked area chart per feed;
> severity donut; NormalizationReport card (duplicates merged, window,
> annualization factor).
> /frequency: asset × week episode heatmap; λ by attack_type animated horizontal
> bars; parameter panel (threshold select, session-window slider) re-querying the
> API and animating bars; the to_explanation() trace rendered as numbered steps
> with monospace numbers.

## Colour was computed, not chosen

Every palette was run through the data-viz validator against this app's chart
surface (`#0A1120`, dark). **The first attempt failed**, which is the argument
for running it:

```
sky #38BDF8 · amber #F59E0B · violet #A78BFA        → FAILED
  [FAIL] Lightness band    all three outside L 0.48–0.67
  [FAIL] CVD separation    violet↔sky ΔE 5.2 (deutan), floor 6
```

The UI accent is too light for the dark band, and sky against violet collapses
under deuteranopia. The documented slots pass on the same surface:

```
#3987e5 · #d95926 · #199e70                          → ALL PASS (--pairs all)
  worst CVD ΔE 9.4 (target 8) · normal-vision ΔE 20.9 (floor 15) · contrast ≥3:1

ordinal ramp #184f95 → #9ec5f4                       → ALL PASS (--ordinal)
  monotone L · adjacent ΔL ≥ 0.06 · light end 2.33:1 (floor 2.0) · hue spread 3°
```

**The UI accent stays chrome only** — focus, active route, links. It is
deliberately not a series colour, so a blue mark inside a chart always means a
series and never "this is interactive".

## Colour job per chart

| Chart | Job | Encoding |
|---|---|---|
| Funnel | ordered stages | ordinal ramp, one hue, monotone |
| Weekly area | three series to tell apart | categorical slots 1–3 |
| Severity donut | **ordered** scale | ordinal ramp; `unknown` off-ramp in neutral |
| λ by attack type | one measure, **nominal** categories | one hue for every bar |
| Asset × week heatmap | continuous magnitude | sequential ramp + scale legend |

Two of these are the anti-pattern the catalog warns about most directly.
**λ bars are nominal**, so colouring them light-to-dark by value would spend the
identity channel re-encoding what bar length already shows — every bar takes the
same hue, and with one series there is no legend box. **Severity is ordered**, so
it does take the ramp; `unknown` sits deliberately *off* it in a neutral, because
an ungraded event is unknown, not mild.

## Decisions taken

1. **The funnel does not colour its first stage by feed.** The SIEM/EDR split
   rides the caption instead. Splitting that bar into two feed hues would put a
   categorical job (identity) inside an ordinal chart (position), and the reader
   would hold two meanings for one channel.
2. **The donut direct-labels every segment** with count and share. A donut
   compares close values badly and two of these are within 3% of each other, so
   nobody should have to judge one arc against another.
3. **Every chart has a table view**, toggled in its own header. A colour-encoded
   chart gates its values behind vision and behind hovering; the table is the
   WCAG-clean twin that makes the tooltip an enhancement rather than the only way
   in.
4. **The parameter panel is one row above everything it scopes**, never inside a
   chart card, so both charts and all three stat tiles always describe the same
   slice.
5. **Refetch holds the previous render at 45% opacity.** No skeleton flash, no
   layout jump. A stale request that lands after a newer one is discarded by
   ticket, so dragging the slider cannot leave an out-of-date answer on screen.
6. **`λ = 0` types are drawn and labelled "not observable", not dropped.** A
   missing row reads as "not applicable"; a labelled zero reads as "we looked and
   could not see it", which is what `UNOBSERVABLE_ATTACK_TYPES` actually means.
7. **The trace is rendered verbatim** from `to_explanation()`, with monospace
   numbers so quantities in adjacent steps line up. Paraphrasing it would let the
   page drift from the engine.
8. **Heatmap cells are buttons.** The hit target is the whole cell plus its gap,
   each carries an `aria-label` with asset, week and count, and hover and focus
   show the same readout.

## One backend change inside a `feat(web)` commit

The heatmap needs episodes per asset *per week*, which no endpoint exposed.
`AssetFrequency` gained `episodes_by_week` (ISO Monday → count, quiet weeks
absent rather than zero-filled) and the serializer exposes it. Small, but it is
engine scope inside a frontend commit and worth naming.

## Verified

Both pages served against a live API: `/telemetry` renders the funnel, weekly
area, donut and normalization card with the annualization factor at 1.721698;
`/frequency` renders the panel, λ bars, a 620-cell heatmap (20 assets × 31 weeks)
and a 7-step trace. 241 backend tests pass, lint and typecheck clean, both routes
build dynamic.

**Still unverified visually.** Browser tooling is unavailable in this session, so
nobody has looked at these pages. Recharts measures the DOM, so the λ bars and
the area chart are blank in server HTML and appear on hydration — normal, but it
means the structural check cannot speak to the rendered geometry. Label
collisions, the heatmap's horizontal scroll on a narrow viewport, and the donut's
legend wrapping are exactly what a visual pass would catch.
