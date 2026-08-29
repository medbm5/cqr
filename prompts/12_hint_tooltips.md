# 12 — Plain-language hint tooltips

**Commit:** `feat(web): plain-language hint tooltips for all mathematical concepts`

## Prompt given

> Add plain-language hint tooltips for every mathematical concept in the UI.
>
> 1. Reusable `components/HintTip.tsx` — ⓘ after a label; hover **and** click/tap;
>    max-width ~280px; dark card matching the design system; framer-motion
>    fade+scale ~150ms; dismiss on outside click / Esc; accessible (button
>    element, `aria-describedby`, focusable); never truncate or overflow the
>    viewport (flip placement near edges).
> 2. Single source of truth `lib/glossary.ts` — typed
>    `GLOSSARY: { [key]: { term, hint } }`. All copy lives here, nowhere inline.
>    **Use exactly these entries (edit nothing without asking)** — 27 entries
>    supplied verbatim.
> 3. Wire them in everywhere the concepts appear. **Grep for each GLOSSARY key's
>    concept to make sure none is missed; list any concept you find in the UI
>    that has no glossary entry instead of writing copy yourself.**
> 4. Don't duplicate: keep the subtitle *and* add the tooltip — "subtitle is the
>    reminder, tooltip is the lesson."
> 5. Component tests: renders on hover and on click, closes on Esc, and a test
>    importing the glossary and grepping usage so every key is referenced by at
>    least one page (drift guard).

## Decisions taken

**The copy was used verbatim.** All 27 entries are byte-for-byte what was
supplied. Nothing was edited, shortened, or "improved".

**Two hint slots per figure, not one.** A `StatTile` takes `term` (beside the
label) *and* `captionTerm` (beside the caption). The severity median tile is the
case that forced it: the label is the concept (`median_incident`), the caption
names the parameter behind it (`exp(μ) with μ = 10.573` → `mu`). Collapsing them
to one ⓘ would have orphaned six entries — μ, σ, `median_year`, `annualization`,
`p_materialize`, `attack_grade` — or forced the copy to be rewritten to cover
two ideas at once. `ChartFrame` got the same pair (`term`, `hintTerm`) for the
QQ plot: the title is the diagnostic, the hint line quotes a KS distance.

**Captions were kept, per requirement 4.** No existing subtitle was deleted.

**Hints sit beside `<label for>`, never inside it.** A `<button>` inside a
`for`-bound label activates the labelled control on every click, so the
frequency threshold select would have changed value each time a reader asked
what "attack-grade" means. The two param panels and the simulation run controls
were restructured into a flex row: label, then ⓘ, then the control.

**Hover opens, click *pins*.** Leaving with the pointer closes an unpinned hint
but not a pinned one — a 280px card cannot be read while holding the mouse
still, and a phone has no hover at all. Focus opens it too, so the hints are not
gated behind a pointing device.

## Placement

| Page | Entries reachable |
|---|---|
| `/` | `aal`, `median_year`, `dedup`, `lambda_detected`, `lambda_incident` |
| `/telemetry` | `dedup`, `attack_grade`, `episode`, `lambda_incident`, `annualization` |
| `/frequency` | `lambda_detected`, `annualization`, `episode`, `attack_grade`, `lambda_incident`, `p_materialize`, `session_window` |
| `/severity` | `median_incident`, `mu`, `mean_incident`, `sigma`, `peer_weight`, `kish_neff`, `fallback`, `lognormal`, `qq_plot`, `ks` |
| `/simulation` | `aal`, `median_year`, `var95`, `tvar95`, `var99`, `tvar99`, `monte_carlo`, `poisson`, `seed` |

All 27 render; verified against the live API by counting distinct
`aria-label="What is …?"` attributes in each page's HTML.

## Concepts in the UI with no glossary entry

Reported rather than written, per requirement 3:

1. **OEP / AEP and return period** — `/simulation`, the exceedance-curve chart.
   The legend explains the pair in eight words ("AEP — the year's total", "OEP —
   largest single loss") and the axis is labelled "1-in-N-year", but neither
   *exceedance curve* nor *return period* has an entry. This is the largest gap:
   it is a whole chart with no ⓘ on it.
2. **Pareto tail and α** — `/severity`, in the QQ plot's hint line when the tail
   rival wins ("a Pareto tail (α 2.31) fits the extremes better"). A reader is
   told a second distribution beat the lognormal in the tail, with no route to
   what that means or why it matters for VaR.
3. **Gaussian kernel and bandwidth h** — `/severity`, peer-group card, both in
   the formula `exp(−d² / 2h²)` and the row "Gaussian kernel on |maturity − 55|,
   h = 15". `peer_weight` covers *that* peers are softly weighted, not *how* the
   maturity kernel decays.
4. **Inflation avoided** — `/telemetry`, normalization report ("Concatenating
   instead would overstate by 42.3%"). Adjacent to `dedup` but a distinct
   quantity: the overstatement a naive merge would produce.
5. **"not observable"** — `/frequency`, λ-by-type bars. Attack types the
   telemetry structurally cannot see are marked, and the mark is unexplained.

A test also pins the inverse: a `term=` pointing at a key the glossary does not
define fails the suite, so none of the above can be wired without copy first.

## Test runner

The frontend had none, so this feature adds one: **vitest + @testing-library/react
+ jsdom**, `npm test`, wired into `make test` (and `npm run typecheck` into
`make lint`). 13 tests:

- `tests/hint-tip.test.tsx` (9) — hidden until asked; opens on hover and closes
  on unhover; opens on click and *survives* unhover; second click closes;
  Escape closes and returns focus to the trigger; outside click closes; keyboard
  focus opens; `aria-describedby` points at the tooltip only while showing;
  the accessible name names the concept.
- `tests/glossary-coverage.test.ts` (4) — the drift guard (every entry is
  rendered by some page), the inverse guard (no `term=` at an undefined key), a
  check that no hint string was copied into a component, and shape checks on the
  copy itself.

The removal assertions wait rather than asserting on the same tick:
`AnimatePresence` keeps the node mounted through its 150ms exit, and asserting
instantly fails on an animation doing exactly its job.
