"""Turning alerts into attacks.

An alert is not an attack. A single intrusion produces a burst of detections -
one per stage, per rule, per sensor - and counting alerts as attacks would
overstate frequency by whatever the estate's detection verbosity happens to be.
This module collapses bursts into *episodes*, the unit the frequency model
actually counts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise

from risk_engine.ingestion import SecurityEvent, SeverityClass

from .attack_types import AttackType, attack_type_for

#: Default severity at or above which an event is treated as attack-grade.
DEFAULT_SEVERITY_THRESHOLD = SeverityClass.HIGH

#: Default quiet period that ends an episode, in hours. A day of silence on an
#: asset is taken to separate two attacks rather than to interrupt one.
DEFAULT_SESSION_GAP_HOURS = 24.0

#: Days in a year, for annualization. Not a parameter: a leap year would change
#: the fourth decimal of a figure whose inputs are far less precise than that.
DAYS_PER_YEAR = 365.0


@dataclass(frozen=True, slots=True)
class FrequencyParams:
    """Knobs of the frequency model, carried alongside every estimate.

    Attributes:
        severity_threshold: Minimum severity for an event to count as
            attack-grade. Events graded below it are noise for this purpose, and
            events with no grade at all are excluded rather than assumed benign.
        session_gap_hours: Quiet period that ends an episode. Consecutive events
            separated by at most this much belong to the same episode.
    """

    severity_threshold: SeverityClass = DEFAULT_SEVERITY_THRESHOLD
    session_gap_hours: float = DEFAULT_SESSION_GAP_HOURS

    def __post_init__(self) -> None:
        """Reject a gap that would make sessionization meaningless."""
        if self.session_gap_hours <= 0:
            raise ValueError(f"session_gap_hours must be positive, got {self.session_gap_hours}")

    @property
    def session_gap(self) -> timedelta:
        """The quiet period as a `timedelta`."""
        return timedelta(hours=self.session_gap_hours)


@dataclass(frozen=True, slots=True)
class Episode:
    """One attack: a burst of attack-grade events on one asset, of one type.

    Attributes:
        asset_id: The asset under attack.
        attack_type: What the episode is counted as, for pricing against the
            external incident base.
        started_at: First attack-grade event in the burst.
        ended_at: Last attack-grade event in the burst.
        event_count: How many events the episode absorbed. High counts are a
            detection-verbosity signal, not a severity signal.
        peak_severity: Worst severity observed within the episode.
    """

    asset_id: str
    attack_type: AttackType
    started_at: datetime
    ended_at: datetime
    event_count: int
    peak_severity: SeverityClass

    @property
    def duration_hours(self) -> float:
        """Elapsed time between the first and last event of the episode."""
        return (self.ended_at - self.started_at).total_seconds() / 3600.0


def is_attack_grade(event: SecurityEvent, threshold: SeverityClass) -> bool:
    """Whether an event is severe enough to count toward an attack.

    An event with no severity grade is *not* attack-grade. That is deliberate:
    the SIEM leaves 317 rows ungraded and the EDR sentinel accounts for 6 more
    (`notebooks/01_eda.ipynb` section 4), and promoting them would invent
    attacks while demoting them silently would hide them. They are excluded here
    and counted in the explanation instead.

    Args:
        event: The event to test.
        threshold: Minimum severity class to qualify.

    Returns:
        True when the event carries a grade at or above the threshold.
    """
    if event.severity_class is None:
        return False
    return event.severity_class.rank >= threshold.rank


def sessionize(events: Sequence[SecurityEvent], *, params: FrequencyParams) -> tuple[Episode, ...]:
    """Group attack-grade events into episodes.

    Events are bucketed by `(asset_id, attack_type)` and then split wherever the
    gap between consecutive events exceeds `params.session_gap_hours`.

    Keying on the attack type as well as the asset - rather than on the asset
    alone - means two campaigns of different types running against one machine on
    the same day are counted as two attacks, not one. It also removes the need
    for a rule that picks a single attack type for a mixed episode, which would
    otherwise decide, arbitrarily, which of two concurrent attacks gets priced.
    On the case data the two readings differ by a factor of 5.7 in the total
    rate, so the choice is recorded here rather than left implicit.

    Events with no `asset_id` are excluded: an attack that cannot be attributed
    to a machine cannot be clustered per machine. They are counted by the caller.

    Args:
        events: Canonical events from the ingestion stage, in any order.
        params: Severity threshold and session gap.

    Returns:
        Episodes sorted by start time, then asset, then attack type - so the
        output does not depend on the order events arrived in.
    """
    buckets: dict[tuple[str, AttackType], list[SecurityEvent]] = defaultdict(list)
    for event in events:
        if event.asset_id is None or not is_attack_grade(event, params.severity_threshold):
            continue
        buckets[(event.asset_id, attack_type_for(event.technique))].append(event)

    episodes: list[Episode] = []
    for (asset_id, attack_type), bucket in buckets.items():
        bucket.sort(key=lambda event: (event.observed_at, event.event_id))
        run: list[SecurityEvent] = [bucket[0]]
        for previous, current in pairwise(bucket):
            if current.observed_at - previous.observed_at > params.session_gap:
                episodes.append(_close(asset_id, attack_type, run))
                run = []
            run.append(current)
        episodes.append(_close(asset_id, attack_type, run))

    return tuple(
        sorted(
            episodes,
            key=lambda episode: (episode.started_at, episode.asset_id, episode.attack_type),
        )
    )


def _close(asset_id: str, attack_type: AttackType, run: list[SecurityEvent]) -> Episode:
    """Build an episode from a completed run of events."""
    severities = [event.severity_class for event in run if event.severity_class is not None]
    return Episode(
        asset_id=asset_id,
        attack_type=attack_type,
        started_at=run[0].observed_at,
        ended_at=run[-1].observed_at,
        event_count=len(run),
        peak_severity=max(severities, key=lambda severity: severity.rank),
    )
