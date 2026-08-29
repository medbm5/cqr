"""Canonical types produced by ingestion.

Everything downstream of this module works on `SecurityEvent` and `Asset`; the
feed-specific column names, severity vocabularies and timestamp formats stop
here. The types are frozen so a pipeline stage cannot mutate the events it was
handed, which is what makes a run reproducible from its inputs alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

#: Numeric severity of each class, shared by both feeds.
#:
#: The SIEM emits these four classes directly; the EDR's numeric score is mapped
#: onto them at the cut points derived in `notebooks/01_eda.ipynb` section 4. The
#: 0.25/0.5/0.75/1.0 spacing is a modeling convention, not a measurement: it makes
#: "Critical" exactly four times "Low" so that severity-weighted counts stay
#: interpretable.
SEVERITY_SCORES: dict[str, float] = {
    "low": 0.25,
    "medium": 0.50,
    "high": 0.75,
    "critical": 1.00,
}


class SeverityClass(StrEnum):
    """Severity vocabulary shared by every feed, ordered from least to most severe."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def score(self) -> float:
        """Numeric severity in [0, 1] for this class."""
        return SEVERITY_SCORES[self.value]

    @property
    def rank(self) -> int:
        """Position in the ordering, 0 for `LOW` through 3 for `CRITICAL`.

        Severity classes are compared by rank rather than by string value, so
        `max()` over a set of classes returns the worst one.
        """
        return _CLASS_RANK[self]


_CLASS_RANK: dict[SeverityClass, int] = {
    SeverityClass.LOW: 0,
    SeverityClass.MEDIUM: 1,
    SeverityClass.HIGH: 2,
    SeverityClass.CRITICAL: 3,
}


class Source(StrEnum):
    """A telemetry feed an event was observed in."""

    SIEM = "siem"
    EDR = "edr"


@dataclass(frozen=True, slots=True)
class Asset:
    """One entry of the company asset reference.

    The asset reference is the only source of business context in the pipeline:
    the telemetry feeds carry an identifier but know nothing about what the
    machine behind it is worth (`notebooks/01_eda.ipynb` section 5 shows event
    severity is statistically independent of criticality and environment).
    """

    asset_id: str
    asset_type: str
    business_criticality: int
    environment: str


@dataclass(frozen=True, slots=True)
class SecurityEvent:
    """One security detection, normalized across feeds.

    Attributes:
        event_id: Identifier of the event. For an event seen in both feeds this
            is the SIEM identifier, the SIEM being the feed with the richer
            schema; the EDR identifier is not retained because it carries no
            information the merged event does not already hold.
        asset_id: Asset the event was observed on, or `None` when the feed did
            not report one. A null asset cannot be attributed, so such events
            are counted in totals but never merged across feeds.
        technique: MITRE ATT&CK technique, or `None` when the feed did not
            report one.
        severity_score: Severity in [0, 1], or `None` when no feed graded the
            event. Unknown severity is propagated rather than defaulted, so a
            missing grade can never be mistaken for a benign one.
        severity_class: The class matching `severity_score`, or `None`.
        observed_at: Detection time, timezone-aware UTC.
        sources: Feeds the event was observed in, ordered `siem` before `edr`.
    """

    event_id: str
    asset_id: str | None
    technique: str | None
    severity_score: float | None
    severity_class: SeverityClass | None
    observed_at: datetime
    sources: tuple[Source, ...]

    def __post_init__(self) -> None:
        """Reject events that violate the invariants the rest of the engine assumes."""
        if self.observed_at.tzinfo is None:
            raise ValueError(f"observed_at must be timezone-aware: {self.event_id}")
        if (self.severity_score is None) != (self.severity_class is None):
            raise ValueError(
                f"severity_score and severity_class must both be set or both be None: "
                f"{self.event_id}"
            )
        if not self.sources:
            raise ValueError(f"event must carry at least one source: {self.event_id}")

    @property
    def has_dedup_key(self) -> bool:
        """Whether the event can be matched against the other feed.

        Cross-feed identity is the triple (asset, technique, timestamp). An event
        missing either of the first two cannot take part in that comparison, in
        either direction.
        """
        return self.asset_id is not None and self.technique is not None

    @property
    def dedup_key(self) -> tuple[str, str, datetime]:
        """The cross-feed identity triple.

        Returns:
            `(asset_id, technique, observed_at)`.

        Raises:
            ValueError: If the event has an incomplete key. Guard with
                `has_dedup_key` before calling.
        """
        if self.asset_id is None or self.technique is None:
            raise ValueError(f"event has no dedup key: {self.event_id}")
        return (self.asset_id, self.technique, self.observed_at)


def as_utc(moment: datetime) -> datetime:
    """Return `moment` as timezone-aware UTC.

    Both feeds export naive timestamps with no zone designator. They are read as
    UTC rather than as local time: the two feeds agree to the second on 12,343
    events (`notebooks/01_eda.ipynb` section 3), so they share one clock, and
    treating that clock as UTC keeps the pipeline free of a host-dependent
    offset that would silently shift every window boundary.

    Args:
        moment: A naive or timezone-aware datetime.

    Returns:
        The same instant, timezone-aware in UTC.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)
