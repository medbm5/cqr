"""Cross-feed deduplication.

The SIEM and the EDR describe the same estate with different schemas. On the case
data 12,343 detections carry an identical (asset, technique, timestamp) triple in
both feeds - 67% of everything the EDR reports, agreeing to the second. They are
two partial observers of one event stream, not two independent streams
(`notebooks/01_eda.ipynb` section 3).

Concatenating the two feeds would therefore report 45,840 rows for 32,193 events:
31,701 that carry a complete key and can be reconciled, plus 492 that cannot
(105 SIEM rows with no asset, 387 EDR rows with no technique) and are carried
through unmatched. That is a 42.4% inflation applied to every annualized
frequency, and so to the final loss.

The notebook's section 3 quotes 31,701 and 44.6%: it measures only the events
that can take part in cross-feed identity, which is the right denominator for
judging how far the feeds overlap. This module reports 32,193 and 42.4%, the
right denominator for how many events the model will actually see. The two
differ by exactly the 492 unmatchable events.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from .loaders import LoadedFeed, observed_window
from .models import Asset, SecurityEvent, SeverityClass, Source
from .report import NormalizationReport, TimeWindow

#: Canonical ordering of sources on a merged event.
_SOURCE_ORDER: tuple[Source, ...] = (Source.SIEM, Source.EDR)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """The output of the ingestion stage.

    Attributes:
        events: Canonical events, deduplicated across feeds and sorted by
            observation time then event id, so a run is byte-for-byte
            reproducible regardless of the order rows arrived in.
        report: The full accounting from rows read to events emitted.
    """

    events: tuple[SecurityEvent, ...]
    report: NormalizationReport

    def to_explanation(self) -> list[str]:
        """Render the run as a numbered, human-readable trace."""
        return self.report.to_explanation()


def merge_feeds(
    siem: LoadedFeed,
    edr: LoadedFeed,
    *,
    assets: Sequence[Asset] = (),
    window: TimeWindow | None = None,
) -> IngestionResult:
    """Combine both feeds into one deduplicated event stream.

    Two reports describe the same event when they share the triple
    `(asset_id, technique, observed_at)`. Matching is done over the *union* of
    both feeds rather than as a pairwise join, because each feed also repeats
    keys internally (761 times in the SIEM, 543 in the EDR on the case data): an
    inner join on those keys multiplies duplicates on both sides and returns
    13,055 rows against 12,343 true matches.

    Where the two feeds disagree on severity the **worst observed signal wins**.
    A detector that graded an event Critical saw something the other missed, and
    a defender has to act on the worse of the two readings; taking the lower
    grade would let one noisy sensor mask the other's finding. An unknown grade
    never wins over a known one - it carries no information to prefer.

    Events whose key is incomplete are never matched, in either direction. The
    feed reported no asset or no technique for them, so there is nothing to
    compare; they are carried through as distinct events rather than dropped or
    fuzzy-matched onto a null.

    Args:
        siem: Output of `load_siem`.
        edr: Output of `load_edr`.
        assets: The asset reference, used to flag events on identifiers it does
            not contain. Optional - pass it to populate that part of the report.
        window: Observation window to record. Defaults to the window spanned by
            the merged events, which is the intended use; pass one explicitly
            only to record a window wider than what was observed.

    Returns:
        The deduplicated events and the report accounting for them.

    Raises:
        ValueError: If both feeds are empty, leaving no window to derive.
    """
    merged: dict[tuple[str, str, datetime], SecurityEvent] = {}
    unmatchable: list[SecurityEvent] = []
    duplicates_merged = 0

    for event in (*siem.events, *edr.events):
        if not event.has_dedup_key:
            unmatchable.append(event)
            continue

        key = event.dedup_key
        existing = merged.get(key)
        if existing is None:
            merged[key] = event
        else:
            merged[key] = _combine(existing, event)
            duplicates_merged += 1

    events = tuple(
        sorted(
            (*merged.values(), *unmatchable),
            key=lambda event: (event.observed_at, event.event_id),
        )
    )

    known_asset_ids = {asset.asset_id for asset in assets}
    unknown_ids: set[str] = set()
    events_on_unknown = 0
    if known_asset_ids:
        for event in events:
            if event.asset_id is not None and event.asset_id not in known_asset_ids:
                unknown_ids.add(event.asset_id)
                events_on_unknown += 1

    report = NormalizationReport(
        feeds=(siem.report, edr.report),
        window=window if window is not None else observed_window(events),
        duplicates_merged=duplicates_merged,
        events_in_both_feeds=sum(1 for event in events if len(event.sources) > 1),
        total_events=len(events),
        unknown_asset_ids=tuple(sorted(unknown_ids)),
        events_on_unknown_assets=events_on_unknown,
    )
    return IngestionResult(events=events, report=report)


def _combine(first: SecurityEvent, second: SecurityEvent) -> SecurityEvent:
    """Collapse two reports of the same event into one canonical event.

    Keeps the worst severity of the two and the union of their sources. The
    identifier of the SIEM report is preferred, the SIEM having the richer
    schema; between two reports from the same feed the lexicographically smaller
    identifier wins, so the result does not depend on row order.
    """
    sources = tuple(
        source for source in _SOURCE_ORDER if source in {*first.sources, *second.sources}
    )
    severity = _worst_severity(first.severity_class, second.severity_class)

    primary = first
    if (Source.SIEM in second.sources and Source.SIEM not in first.sources) or (
        first.sources == second.sources and second.event_id < first.event_id
    ):
        primary = second

    return SecurityEvent(
        event_id=primary.event_id,
        asset_id=primary.asset_id,
        technique=primary.technique,
        severity_score=None if severity is None else severity.score,
        severity_class=severity,
        observed_at=primary.observed_at,
        sources=sources,
    )


def _worst_severity(
    first: SeverityClass | None, second: SeverityClass | None
) -> SeverityClass | None:
    """Return the more severe of two grades, ignoring unknowns.

    An unknown grade is not evidence of a low one, so a known grade always wins
    over `None`; two unknowns stay unknown.
    """
    if first is None:
        return second
    if second is None:
        return first
    return max(first, second, key=lambda severity: severity.rank)
