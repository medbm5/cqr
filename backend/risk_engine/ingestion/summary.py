"""Aggregations of normalized telemetry, for display.

These belong to the engine rather than to the API layer: a weekly event count is
still a statement about the data, and putting it behind the HTTP boundary would
make it untestable without a server and unreproducible from a notebook.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from .models import SecurityEvent, SeverityClass, Source

#: Label used for events no feed graded, so an unknown severity is visible in a
#: chart rather than silently dropped from it.
UNKNOWN_SEVERITY = "unknown"


@dataclass(frozen=True, slots=True)
class WeeklyBucket:
    """Event counts for one week.

    Attributes:
        week_start: Monday of the week, UTC.
        siem_only: Events only the SIEM reported.
        edr_only: Events only the EDR reported.
        both: Events both feeds reported, counted once.
        merged: Distinct events in the week - the sum of the three above, and
            the number the model actually sees.
    """

    week_start: date
    siem_only: int
    edr_only: int
    both: int
    merged: int


@dataclass(frozen=True, slots=True)
class TelemetrySummary:
    """Shape of the normalized telemetry over the observation window.

    Attributes:
        weekly: One bucket per week, ascending. Gaps would show as missing
            weeks; on the case data there are none.
        severity_mix: Distinct events per severity class, plus `unknown`.
        events_by_source: Distinct events per feed combination.
        techniques: The most frequent MITRE techniques, descending.
    """

    weekly: tuple[WeeklyBucket, ...]
    severity_mix: Mapping[str, int]
    events_by_source: Mapping[str, int]
    techniques: Mapping[str, int]


def summarize_telemetry(
    events: Sequence[SecurityEvent], *, top_techniques: int = 15
) -> TelemetrySummary:
    """Aggregate normalized events into the series a dashboard needs.

    Args:
        events: Canonical events from `merge_feeds`.
        top_techniques: How many techniques to include, by descending frequency.

    Returns:
        The summary. Every count is of *distinct* events, so nothing here can
        disagree with the event total the ingestion report gives.
    """
    weeks: dict[date, Counter[str]] = {}
    severity: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    techniques: Counter[str] = Counter()

    for event in events:
        moment = event.observed_at.date()
        week_start = moment - timedelta(days=moment.weekday())
        bucket = weeks.setdefault(week_start, Counter())

        label = _source_label(event)
        bucket[label] += 1
        bucket["merged"] += 1
        sources[label] += 1

        severity[
            event.severity_class.value if event.severity_class is not None else UNKNOWN_SEVERITY
        ] += 1
        if event.technique is not None:
            techniques[event.technique] += 1

    weekly = tuple(
        WeeklyBucket(
            week_start=week_start,
            siem_only=bucket["siem"],
            edr_only=bucket["edr"],
            both=bucket["both"],
            merged=bucket["merged"],
        )
        for week_start, bucket in sorted(weeks.items())
    )

    ordered_severity = {member.value: severity.get(member.value, 0) for member in SeverityClass}
    if severity.get(UNKNOWN_SEVERITY):
        ordered_severity[UNKNOWN_SEVERITY] = severity[UNKNOWN_SEVERITY]

    return TelemetrySummary(
        weekly=weekly,
        severity_mix=ordered_severity,
        events_by_source=dict(sources.most_common()),
        techniques=dict(techniques.most_common(top_techniques)),
    )


def _source_label(event: SecurityEvent) -> str:
    """Which feed - or both - reported an event."""
    if len(event.sources) > 1:
        return "both"
    return Source(event.sources[0]).value
