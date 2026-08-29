"""Audit trail for the ingestion stage.

Every number the engine publishes has to be reconstructable from its inputs.
Ingestion is where the row counts change most - rows are dropped, merged and
reclassified - so it is where an unexplained discrepancy is easiest to introduce
and hardest to notice. These records exist so that the difference between "rows
in the CSVs" and "events the model saw" is always fully accounted for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import Source


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """The observation period the telemetry covers.

    Attributes:
        start: First observed detection, UTC.
        end: Last observed detection, UTC.
        observed_days: Distinct calendar days spanned, inclusive of both ends.
    """

    start: datetime
    end: datetime
    observed_days: int

    @property
    def annualization_factor(self) -> float:
        """Multiplier turning a count over this window into an annual rate.

        Counted in calendar days rather than elapsed seconds. On the case data
        the two agree to seven significant figures (211.998 elapsed days against
        212 calendar days, `notebooks/01_eda.ipynb` section 2); the integer is
        preferred because it survives partial first and last days.
        """
        return 365.0 / self.observed_days


@dataclass(frozen=True, slots=True)
class FeedReport:
    """What one feed contributed, and what was set aside on the way in.

    Attributes:
        source: Which feed this describes.
        rows_read: Rows present in the CSV.
        events: Events emitted after per-row exclusions.
        rows_out_of_window: Rows discarded for falling outside the requested
            observation window.
        rows_missing_timestamp: Rows discarded for having no usable timestamp.
            Such a row can be neither windowed nor clustered into an episode.
        rows_incomplete_key: Events kept but unable to take part in cross-feed
            matching, because the feed reported no asset or no technique.
        rows_unknown_severity: Events kept with no severity grade - the SIEM left
            it blank, or the EDR emitted its sentinel.
    """

    source: Source
    rows_read: int
    events: int
    rows_out_of_window: int = 0
    rows_missing_timestamp: int = 0
    rows_incomplete_key: int = 0
    rows_unknown_severity: int = 0


@dataclass(frozen=True, slots=True)
class NormalizationReport:
    """The full accounting for one ingestion run.

    Attributes:
        feeds: One record per feed, in the order they were merged.
        window: The observation period the surviving events span.
        duplicates_merged: Events that were reported more than once and collapsed
            into a single canonical event. Counts both cross-feed matches and
            repeats within one feed.
        events_in_both_feeds: Canonical events carrying two sources.
        total_events: Canonical events emitted.
        unknown_asset_ids: Asset identifiers seen in telemetry but absent from
            the asset reference, sorted.
        events_on_unknown_assets: Events referring to those identifiers.
    """

    feeds: tuple[FeedReport, ...]
    window: TimeWindow
    duplicates_merged: int
    events_in_both_feeds: int
    total_events: int
    unknown_asset_ids: tuple[str, ...] = field(default_factory=tuple)
    events_on_unknown_assets: int = 0

    @property
    def rows_read(self) -> int:
        """Total rows read across every feed."""
        return sum(feed.rows_read for feed in self.feeds)

    @property
    def inflation_avoided(self) -> float:
        """Fraction by which naive concatenation would have overstated the count.

        This is the reason the stage exists. On the case data the two feeds
        overlap on 12,343 events, so concatenating them reports 45,840 rows for
        32,193 distinct events - a 42.4% inflation applied to every annualized
        frequency, and so to the final loss.

        Measured against the events emitted here, which include the 492 that
        carry no usable key and so could never be reconciled. Section 3 of the
        notebook excludes those and quotes 44.6% against 31,701 matchable events;
        see `merge.py` for why both figures are correct.
        """
        if self.total_events == 0:
            return 0.0
        return sum(feed.events for feed in self.feeds) / self.total_events - 1.0

    def to_explanation(self) -> list[str]:
        """Render the run as a numbered, human-readable trace.

        Returns:
            One line per step, in the order the steps happened, such that the
            arithmetic from rows read to events emitted can be checked by hand.
        """
        lines: list[str] = []

        for feed in self.feeds:
            lines.append(f"Read {feed.rows_read:,} rows from the {feed.source.value.upper()} feed.")
            if feed.rows_missing_timestamp:
                lines.append(
                    f"  Dropped {feed.rows_missing_timestamp:,} row(s) with no usable "
                    f"timestamp: they can be neither windowed nor clustered."
                )
            if feed.rows_out_of_window:
                lines.append(
                    f"  Dropped {feed.rows_out_of_window:,} row(s) outside the requested "
                    f"observation window."
                )
            lines.append(f"  Kept {feed.events:,} event(s).")
            if feed.rows_incomplete_key:
                lines.append(
                    f"  {feed.rows_incomplete_key:,} of them have no asset or no technique, "
                    f"so they cannot be matched against the other feed and are carried as "
                    f"distinct events."
                )
            if feed.rows_unknown_severity:
                lines.append(
                    f"  {feed.rows_unknown_severity:,} of them carry no severity grade; "
                    f"severity is left unknown rather than defaulted."
                )

        naive = sum(feed.events for feed in self.feeds)
        lines.append(
            f"Merged both feeds on (asset_id, technique, observed_at): "
            f"{naive:,} event(s) collapsed to {self.total_events:,} distinct event(s)."
        )
        lines.append(
            f"  {self.duplicates_merged:,} duplicate report(s) were absorbed, of which "
            f"{self.events_in_both_feeds:,} event(s) were seen by both feeds."
        )
        lines.append(
            f"  Concatenating the feeds instead would have overstated the event count by "
            f"{self.inflation_avoided:.1%}."
        )
        lines.append("  Where the two feeds disagreed on severity, the worse grade was kept.")

        if self.unknown_asset_ids:
            shown = ", ".join(self.unknown_asset_ids[:5])
            hidden = len(self.unknown_asset_ids) - 5
            more = f", +{hidden} more" if hidden > 0 else ""
            lines.append(
                f"{self.events_on_unknown_assets:,} event(s) reference "
                f"{len(self.unknown_asset_ids)} asset id(s) absent from the asset reference "
                f"({shown}{more}); they are kept and flagged, not dropped."
            )

        lines.append(
            f"Observation window {self.window.start:%Y-%m-%d} to {self.window.end:%Y-%m-%d} "
            f"= {self.window.observed_days} calendar day(s); annualization factor "
            f"365 / {self.window.observed_days} = {self.window.annualization_factor:.6f}."
        )

        # Only top-level steps are numbered; indented lines detail the step above.
        numbered: list[str] = []
        step = 0
        for line in lines:
            if line.startswith("  "):
                numbered.append(line)
            else:
                step += 1
                numbered.append(f"{step}. {line}")
        return numbered
