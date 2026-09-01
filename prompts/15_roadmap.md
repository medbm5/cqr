# 15 — Roadmap page

**Commit:** `feat(web): animated roadmap page — current state, change, impact per next step`

## Prompt given

> Create a /roadmap page in the Next.js app: the product vision beyond the case
> study. Add "Roadmap" to the sidebar nav (last position, small "vision" badge).
>
> **Data** — single source of truth in `lib/roadmap.ts`: typed array of
> `RoadmapItem { id, title, phase: 1|2|3, theme: 'modeling' | 'platform' |
> 'data', current, change, impact, effort: 'S'|'M'|'L' }`. One fixed structure
> per item: current = "What we have", change = "What to change", impact = "How
> it impacts the project". Populate from `next_steps.md` — rewrite each
> deprioritized idea into this structure, don't invent new modeling claims —
> plus authentication & client workspaces, and data-source integrations. Own
> suggestions welcome ONLY as platform/ops items; flag modeling ideas as
> questions instead.
>
> **Design** — vertical timeline spine grouped by phase with sticky headers;
> cards docked to the spine with theme chip and effort badge; Today / Change /
> Impact with a thin divider; framer-motion `whileInView` stagger with
> `once: true`; spine draws itself on scroll progress; expand on click with
> animated height; respect `prefers-reduced-motion`. No new dependencies,
> works on mobile.

## What went in

17 items across three phases — 4 hardening, 5 productization, 8 model depth.
Nine modeling, six platform, two data.

Every modeling entry is a rewrite of a `next_steps.md` section, including the
"why it wasn't done" reasoning, which is carried in the `impact` field because
that is where a reader deciding whether to fund the work actually needs it.
**No modeling idea appears that the document does not already argue for.**

Two `next_steps.md` items became one card: §10 (auth on the API) folded into the
phase-2 workspace item, since the rate-limiting and auth work it describes is a
subset of what multi-tenancy needs. Two "Smaller things" were promoted to cards
— per-asset drilldown, and cross-process caching, the latter extended into run
history because a persisted run is what the workspace work in phase 2 rests on.

Own suggestions, all platform, none touching the model: PDF report export,
monitoring and observability, and the run-history half of the caching item.

Left out as too small to earn a card: the `results.json` schema and the
notebook-versus-engine drift test.

## Decisions taken

**Only the impact section expands.** It is the field that runs long, because it
carries the honest version of why each item was skipped. Truncating the other
two would hide nothing worth reading; truncating this one everywhere would hide
exactly what the page exists to show.

**Height is animated by measurement, not by `layout`.** A framer-motion `layout`
animation interpolates a text block by *scaling* it, which visibly squashes the
glyphs for the length of the transition. The card instead animates the height of
an `overflow-hidden` window around the paragraph, between a collapsed height
expressed in `em` and the measured `scrollHeight`. The type is left alone.
`layout="position"` stays on the article so the cards below slide rather than
jump.

**The collapsed height is `4.875em`, not a measured value.** Three lines of
`text-xs leading-relaxed`. Expressing it in `em` means the server and the first
client frame agree exactly — a measured value would render the box open and snap
it shut on hydration.

**The expand control appears only when something is hidden.** Measured on mount
and on resize. A "Read more" on a paragraph that is already whole is a button
that does nothing, and a reader only discovers that by pressing it. The
consequence is that the control is absent server-side; the full text is still in
the DOM and still read by assistive technology, since `overflow: hidden` does
not hide content from it.

**Sticky phase headers from `lg` up only.** Below that the nav is itself a
sticky strip across the top of the viewport, and a second sticky element would
dock underneath it and never be seen.

**Theme colour is never the only channel.** Every chip carries its theme as
text beside the swatch, which is what frees the three hues to be chosen for
separation on a dark navy ground rather than constrained by a categorical
palette check.

## A question back

**Phase placement of the credibility blend.** `next_steps.md` calls
Gamma-Poisson credibility "still the first thing I would build next", but the
phase names put modeling work in phase 3, so it sits there — first within its
phase, third overall. If the phases are meant to read as delivery order rather
than as kinds of work, that item belongs in phase 1 and the naming needs a
rethink. Left as specified; say the word.

## Tests

10 new (frontend total 42). Data: every item has all three fields and no two of
them are identical; ids are unique; every item sits in a declared phase; no
phase is empty; the nine required items are present. Render: every item appears
under a phase heading, all three section labels appear once per card, the
expand toggle flips `aria-expanded`, and theme and effort are readable as text.
Navigation: Roadmap is last, carries the `vision` badge, and no other entry does.

`tests/setup.ts` gained stubs for `IntersectionObserver` and `ResizeObserver`,
which jsdom does not implement and which `whileInView` and the clip measurement
respectively mount on.
