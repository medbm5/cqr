# 07 — Frontend shell

**Commit:** `feat(web): app shell, nav, design system, animated landing`

## Prompt given

> Build the frontend shell per CLAUDE.md aesthetics: dark risk-cockpit (deep
> navy, one accent), sidebar nav (Overview, Telemetry, Frequency, Severity,
> Simulation), framer-motion page transitions (~200ms fade+slide), reusable Card
> (hover lift), StatTile (label/value/delta), AnimatedCounter, skeleton loaders.
> Landing: hero with the company profile (ETI · Retail · 1,200 employees ·
> maturity 55/100) + four StatTiles from the API (total events, dedup rate,
> λ/year, AAL) via the typed client. Responsive.

## What renders

Verified against both servers running, reading live figures end to end:

```
Distinct events    32.2K      From 45,840 raw rows across two feeds
Deduplicated       29.8%      ▼ 13,647 rows  vs naive concatenation
Attack frequency   9,168/yr   5,325 episodes over 212 observed days
Average annual loss €12.5B    Median year €11.9B · 10,000 simulated years

Profile: ETI · Retail / e-commerce · 1,200 · 55 / 100
Nav:     Overview · Telemetry · Frequency · Severity · Simulation
```

## Design decisions

1. **Every ink token was checked against the surfaces, not chosen by eye.**
   `slate-500`, the obvious muted grey, fails AA on `navy.900` at 3.96:1. The
   muted token is `#7A8AA0` (5.36:1 on card, 4.84:1 on the raised surface).
   Primary 17.2:1, secondary 7.4:1, accent 8.8:1.
2. **The accent marks signal only** — active route, focus ring, a call to action.
   Never decoration, so that when it appears the eye is right to go there. Loss
   severity scales will be defined per chart, so the accent keeps one meaning.
3. **`Card`'s hover lift is opt-in.** A card that rises under the cursor promises
   it does something; a static panel that lifts is a lie the reader discovers by
   clicking. Only the four navigation cards use it.
4. **`StatTile` takes a delta *or* a caption, never both.** Two subtitles under
   one number is two things to read and no hierarchy.
5. **`StatDelta` separates `direction` from `isGood`.** Down is good for
   duplicate rows and bad for detection coverage; a tile that colours by
   direction alone gets one of those wrong. Only one tile has a genuine signed
   baseline (deduplicated, vs naive concatenation) — the rest carry captions,
   because no endpoint supplies a prior period and inventing one would be a
   fabricated trend.
6. **Big figures use proportional digits, not `tabular-nums`.** Tabular gives
   every digit the width of a zero, which reads loose at display sizes. A
   `.tabular` utility exists for the columns that will need it.
7. **`AnimatedCounter` writes the final value to the DOM from the first frame**
   and animates only the visible text, so a screen reader never reads a number
   mid-count. It is skipped entirely under `prefers-reduced-motion`.
8. **The landing is `force-dynamic`.** The first build prerendered it
   *statically* — baking in whatever the API said at build time, or, with the API
   down, a permanently cached "unavailable" page. Caught by reading the build
   output, not by the page failing.
9. **API failure shows an explicit unavailable state, never zeros.** A zero AAL
   is a number someone could act on, and it would be false.

## Two problems worth recording

**The RSC boundary.** `StatTile` is a client component (it animates), and the
landing is a server component, so passing `format={compactNumber}` threw
*"Functions cannot be passed directly to Client Components"*. The prop is now a
serializable `FormatKind` key the client resolves. The data was already arriving
correctly — the error was purely about what may cross that boundary.

**A stale server served a stale contract.** Two dev servers from earlier in the
session were still bound to ports 8000 and 3000. The old API predated this
feature, so it answered `/api/health/` with 200 and every real endpoint with 404,
and the landing rendered its unavailable state against an API that was, by then,
running fine. Diagnosing that meant checking each endpoint rather than trusting
the health probe — a health check that only proves the process is up is a health
check that can mislead.

## Not done

The four inner views are honest placeholders: a page header describing what the
view will answer, skeleton panels, and a line saying it is not built. The data
behind each is already served by the API. Charts were out of scope here and are
where the visualization work actually lands.

**Visual confirmation is outstanding.** Browser tooling was unavailable, so the
page was verified structurally — rendered HTML, live figures, tiles, captions,
navigation, breakpoint coverage — and built clean, but nobody has looked at it.
Layout collisions and spacing are exactly what that check would catch.
