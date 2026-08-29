# 02 — Ingestion & normalization

**Commit:** `feat(ingestion): unified event schema with cross-feed dedup`

## Prompt given

> Build backend/risk_engine/ingestion/ per CLAUDE.md conventions. Canonical
> SecurityEvent: event_id, asset_id, technique, severity_score (0–1),
> severity_class (low/medium/high/critical), observed_at (UTC), sources (list).
> - load_siem(path): Low/Medium/High/Critical → 0.25/0.5/0.75/1.0.
> - load_edr(path): map risk 0–999 to classes/scores using the cut points from the
>   EDA notebook (named constants, comment referencing notebook section 4).
> - merge_feeds(siem, edr): dedup on (asset_id, technique, timestamp); merged
>   events keep sources=["siem","edr"] and max severity (docstring: worst observed
>   signal).
> - load_assets(path): typed asset records.
> - Return a NormalizationReport alongside: rows per feed, duplicates merged,
>   out-of-window rows, unknown assets.
> Pure functions, pandas inside / typed outside. Tests with small fixture CSVs:
> dedup, mapping edges, unknown assets.

## What was produced

`risk_engine/ingestion/` in five modules — `models` (the canonical types),
`scales` (severity translation), `loaders` (CSV → typed records), `merge` (dedup)
and `report` (the audit trail) — plus 63 tests over three fixture CSVs, at 99%
coverage of the package (100% of every module except one line of `cli.py`, which
predates this feature).

Verified against the real data: **12,343 events seen by both feeds**, matching
`notebooks/01_eda.ipynb` section 3 exactly, and a 212-day window giving an
annualization factor of 1.721698.

## Decisions taken (flagged for validation)

1. **`severity_score` and `severity_class` are optional.** The spec describes them
   as always present, but the SIEM leaves 317 rows ungraded and the EDR emits its
   999 sentinel on 6 more. Section 4 of the notebook decided unknown severity must
   propagate as unknown rather than default to Low, so both fields are
   `| None` and a dataclass invariant keeps them set or unset together. Defaulting
   would have understated the attack-grade count that frequency is built on.
2. **`asset_id` and `technique` are optional too**, for the same reason: 105 SIEM
   rows carry no asset and 387 EDR rows no technique. Such events cannot take part
   in cross-feed matching in either direction, so they are carried through
   unmatched (`SecurityEvent.has_dedup_key` is False) rather than dropped or
   fuzzy-joined onto a null. This follows the section 3 decision.
3. **`sources` is a `tuple`, not a `list`.** `SecurityEvent` is a frozen value
   object; a mutable field would make it unhashable and let a later stage edit
   events it was handed. Ordering is canonical, `siem` before `edr`.
4. **Loaders return a `LoadedFeed`** (events plus that feed's `FeedReport`) rather
   than a bare sequence, so `merge_feeds` can assemble the full
   `NormalizationReport` without re-reading the files. `merge_feeds` therefore
   takes two `LoadedFeed`s.
5. **`window` is an optional argument, not a filter that runs by default.** The
   observation window is normally *derived* from the data (`observed_window`), not
   imposed on it; passing one is for the case where a caller wants to restrict the
   period deliberately, and out-of-window rows are then counted in the report.
6. **Naive timestamps are read as UTC.** Neither feed carries a zone. Reading them
   as local time would make every window boundary host-dependent; the two feeds
   agree to the second on 12,343 events, so they share one clock, and calling it
   UTC keeps runs reproducible across machines.
7. **A merged event keeps the SIEM's `event_id`.** The SIEM has the richer schema
   and its identifier is the one an analyst would search for. Between two rows from
   the same feed the lexicographically smaller id wins, so the output does not
   depend on row order — the whole merge is order-independent, and a test asserts
   it by re-running with both feeds reversed.
8. **Unrecognised inputs raise rather than degrade**: an unknown SIEM severity
   label, an EDR risk outside 0–100 that is not the sentinel, a duplicate
   `asset_id`, a missing column. A vocabulary change upstream must not pass as a
   silent downgrade.

## A number that looks like a discrepancy but is not

The module reports **32,193** distinct events and 42.4% inflation; the notebook's
section 3 reports **31,701** and 44.6%. The difference is exactly the 492
unmatchable events (105 + 387). The notebook measures how far the two feeds
overlap, for which only events with a complete key are meaningful; the module
measures how many events the model will see, which includes the unmatchable ones
because decision 2 keeps them. Both figures are correct for their denominator, and
both artefacts now say so explicitly — `merge.py`'s module docstring and a note
added to notebook section 3.

## Not done

`risk_engine/cli.py` still reports every stage as `not_implemented`; wiring the
pipeline was outside this feature's scope. Ingestion is reachable today as a
library, and the smoke check above is the manual equivalent.
