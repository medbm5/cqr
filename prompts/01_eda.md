# 01 — Exploratory data audit (`notebooks/01_eda.ipynb`)

**Commit:** `feat(eda): narrated data audit of the four sources with per-section decisions`

## Prompt given

> Create notebooks/01_eda.ipynb: a narrated data audit of the 4 CSVs in data/
> (schemas in data/README.md). One section per finding, matplotlib charts, and every
> modeling decision ends with a markdown "**Decision:** ..." line. Sections:
> 1. Asset inventory: type × environment × criticality (20 assets).
> 2. Telemetry coverage: events over time per feed; print the exact observed window
>    and derive the annualization factor.
> 3. Cross-feed duplication: join SIEM (asset_id, mitre_technique, detected_at) vs
>    EDR (host, ttp, timestamp); quantify SIEM-only / EDR-only / both (expect ~12.3k
>    shared); conclude the feeds partially observe the same events.
> 4. Severity scales: SIEM class counts vs EDR risk histogram; for overlapping
>    events, cross-tab SIEM severity vs EDR risk quartiles to derive empirical cut
>    points mapping 0–999 → the four classes. Print the chosen cut points.
> 5. Event mix: top MITRE techniques; events by asset criticality and environment.
> 6. Incident base quality: sector mojibake (show and fix), financial_loss_eur == -1
>    sentinels (count, treat as missing), sector/size/attack_type distributions.
> 7. Loss distribution shape: linear + log-scale histograms, skewness, lognormal
>    QQ-plot, mean vs median gap. Decision: heavy tail → fit on log scale.
> 8. Peer group: incidents matching ETI+Retail, then widened (Retail all sizes; ETI
>    all sectors) — show the sample-size vs relevance trade-off motivating soft
>    weighting.
> Keep it presentation-clean.

## What was produced

38 cells (10 figures, 8 rendered tables), executed end to end and committed with
outputs so the notebook reads without being run. Twelve `**Decision:**` lines across
the eight sections, recapped in a closing table that maps each one to the
`risk_engine` sub-package that will implement it.

## Findings that changed the plan

Three results contradict what the brief assumed, and are called out in the notebook
rather than smoothed over:

1. **The EDR scale is 0–100, not 0–999.** 19,344 of 19,350 rows fall in 0–100, the
   99th percentile is 100, and exactly six rows hold 999 — an out-of-band sentinel.
   Ranking those six as genuine scores would place them above every real detection.
2. **A single pooled lognormal is rejected** (KS D=0.107, p≈2e-16) even though the
   log scale is plainly right (skewness 7.4 → 0.80). Splitting by incident severity
   shows why: the base is a mixture of five well-separated strata, three of which
   are individually not rejected. The decision became *lognormal on logs, fitted per
   segment* rather than one global fit.
3. **Both telemetry feeds have gaps and exact duplicate rows** — SIEM missing
   `asset_id` ×105, `severity` ×317, `source` ×1,059; EDR missing `ttp` ×387; 681 and
   543 exactly duplicated rows respectively. Every count in the notebook states what
   it excluded and why.

The headline expectations held: **12,343 events are shared** by both feeds, and the
loss base has median €39,066 / mean €609,836 / max €31.6M.

## Decisions taken (flagged for validation)

1. **EDR cut points 50 / 70 / 94**, derived by grid-searching the triple that
   maximizes agreement with the SIEM label on the 12,887 events both feeds graded.
   87.1% exact agreement, 100.0% within one class. The alternative derivation —
   matching the SIEM's marginal class shares — gives 58/76/98 and only 78.8%
   agreement, so it was rejected: classifying each event correctly matters more than
   reproducing totals.
2. **Annualization uses distinct calendar days (212), not elapsed span (211.998).**
   The two agree to seven significant figures; the integer is preferred because it
   survives partial first and last days.
3. **Mojibake is repaired by a cp1252 → UTF-8 round-trip**, not a lookup table. The
   round-trip fails loudly on undamaged text, which is how clean and damaged labels
   are told apart, and it generalizes to labels beyond the two present here.
4. **`n ≥ 30` per attack-type cell** is the stated threshold for a type-specific
   severity fit. It is a convention, not a derived quantity — but it is what makes
   the peer-group section conclusive, since the exact ETI+Retail group reaches it for
   zero of eight attack types.
5. **Section 3 counts unique keys, not merge rows.** Because both feeds repeat keys
   internally, an inner `merge` returns 13,055 rows against 12,343 true matches. The
   notebook shows both numbers so the discrepancy is not mistaken for an error later.

## Note on the data

`data/` was empty when this ran; the four CSVs and `README.md` were copied in from
the original case archive (`citalid_technical_test_mini_crq.zip`), unmodified —
checksums match the source.
