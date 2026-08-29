"""Readers turning each raw CSV into canonical, typed records.

pandas is used inside these functions for the parsing and vectorized cleaning it
is good at, and does not escape them: every loader returns immutable dataclasses,
so no DataFrame - and no pandas dtype surprise - reaches the modeling stages.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .models import Asset, SecurityEvent, SeverityClass, Source, as_utc
from .report import FeedReport, TimeWindow
from .scales import severity_from_edr_risk, severity_from_siem_label


@dataclass(frozen=True, slots=True)
class LoadedFeed:
    """Events from one feed, with the accounting for what did not make it.

    Attributes:
        events: The canonical events, in file order.
        report: What was read, kept and set aside.
    """

    events: tuple[SecurityEvent, ...]
    report: FeedReport


def load_assets(path: Path | str) -> tuple[Asset, ...]:
    """Read the asset reference.

    Args:
        path: Path to `asset_reference.csv`.

    Returns:
        One `Asset` per row, in file order.

    Raises:
        ValueError: If a required column is missing, if any field is null, or if
            an asset identifier appears twice. The reference is small enough that
            a defect in it is a mistake to fix rather than a condition to absorb,
            and every later join relies on `asset_id` being unique.
    """
    frame = pd.read_csv(path)
    _require_columns(frame, ["asset_id", "asset_type", "business_criticality", "environment"], path)

    if frame.isna().to_numpy().any():
        raise ValueError(f"asset reference contains null values: {path}")

    duplicated = frame.asset_id[frame.asset_id.duplicated()].tolist()
    if duplicated:
        raise ValueError(f"duplicate asset_id in {path}: {sorted(set(duplicated))}")

    return tuple(
        Asset(
            asset_id=str(asset_id),
            asset_type=str(asset_type),
            business_criticality=int(criticality),
            environment=str(environment),
        )
        for asset_id, asset_type, criticality, environment in zip(
            frame.asset_id.tolist(),
            frame.asset_type.tolist(),
            frame.business_criticality.tolist(),
            frame.environment.tolist(),
            strict=True,
        )
    )


def load_siem(path: Path | str, *, window: TimeWindow | None = None) -> LoadedFeed:
    """Read the SIEM export into canonical events.

    Severity arrives as one of four labels and maps directly onto the shared
    vocabulary: Low/Medium/High/Critical to 0.25/0.5/0.75/1.0. A blank severity
    is carried as unknown rather than defaulted to Low - the feed leaves 317 rows
    ungraded on the case data, and treating those as benign would understate the
    attack-grade count.

    Args:
        path: Path to `feed_siem.csv`.
        window: Optional observation window; rows outside it are excluded and
            counted. Omit it to keep every row, which is the usual case since the
            window is normally derived from the data rather than imposed on it.

    Returns:
        The events and the accounting for the rows behind them.

    Raises:
        ValueError: If a required column is missing, or a severity label is
            outside the four known classes.
    """
    frame = pd.read_csv(path, parse_dates=["detected_at"])
    _require_columns(
        frame, ["event_id", "asset_id", "mitre_technique", "severity", "detected_at"], path
    )

    return _build_feed(
        frame=frame,
        source=Source.SIEM,
        id_column="event_id",
        asset_column="asset_id",
        technique_column="mitre_technique",
        timestamp_column="detected_at",
        severities=[
            None if pd.isna(value) else severity_from_siem_label(str(value))
            for value in frame.severity
        ],
        window=window,
    )


def load_edr(path: Path | str, *, window: TimeWindow | None = None) -> LoadedFeed:
    """Read the EDR export into canonical events.

    Severity arrives as a number and is mapped onto the shared classes at the cut
    points derived in `notebooks/01_eda.ipynb` section 4 (see
    `scales.EDR_CUT_POINTS`). The feed's sentinel value is read as unknown
    severity, not as an extreme score.

    Args:
        path: Path to `feed_edr.csv`.
        window: Optional observation window; rows outside it are excluded and
            counted.

    Returns:
        The events and the accounting for the rows behind them.

    Raises:
        ValueError: If a required column is missing, or a risk score is outside
            the observed range without being the known sentinel.
    """
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    _require_columns(frame, ["id", "host", "ttp", "risk", "timestamp"], path)

    if frame.risk.isna().any():
        raise ValueError(f"EDR feed has rows with no risk score: {path}")

    return _build_feed(
        frame=frame,
        source=Source.EDR,
        id_column="id",
        asset_column="host",
        technique_column="ttp",
        timestamp_column="timestamp",
        severities=[severity_from_edr_risk(int(value)) for value in frame.risk],
        window=window,
    )


def observed_window(*feeds: Iterable[SecurityEvent]) -> TimeWindow:
    """Derive the observation window from the events themselves.

    The annualization factor is a first-class model input and must come from the
    data, never from a constant: a longer telemetry export has to change the
    answer automatically.

    Args:
        *feeds: One or more collections of events.

    Returns:
        The window spanned by the union of the events.

    Raises:
        ValueError: If no events were supplied - there is no window to derive.
    """
    moments = [event.observed_at for feed in feeds for event in feed]
    if not moments:
        raise ValueError("cannot derive an observation window from zero events")

    start, end = min(moments), max(moments)
    observed_days = (end.date() - start.date()).days + 1
    return TimeWindow(start=start, end=end, observed_days=observed_days)


def _build_feed(
    *,
    frame: pd.DataFrame,
    source: Source,
    id_column: str,
    asset_column: str,
    technique_column: str,
    timestamp_column: str,
    severities: list[SeverityClass | None],
    window: TimeWindow | None,
) -> LoadedFeed:
    """Assemble canonical events from an already-parsed feed.

    Shared by both loaders: the feeds differ only in their column names and in
    how severity is derived, and both of those are resolved by the caller.
    """
    events: list[SecurityEvent] = []
    missing_timestamp = 0
    out_of_window = 0
    incomplete_key = 0
    unknown_severity = 0

    for row, severity in zip(frame.itertuples(index=False), severities, strict=True):
        moment = getattr(row, timestamp_column)
        if pd.isna(moment):
            missing_timestamp += 1
            continue

        observed_at = as_utc(pd.Timestamp(moment).to_pydatetime())
        if window is not None and not (window.start <= observed_at <= window.end):
            out_of_window += 1
            continue

        asset_id = _optional_str(getattr(row, asset_column))
        technique = _optional_str(getattr(row, technique_column))
        if asset_id is None or technique is None:
            incomplete_key += 1
        if severity is None:
            unknown_severity += 1

        events.append(
            SecurityEvent(
                event_id=str(getattr(row, id_column)),
                asset_id=asset_id,
                technique=technique,
                severity_score=None if severity is None else severity.score,
                severity_class=severity,
                observed_at=observed_at,
                sources=(source,),
            )
        )

    report = FeedReport(
        source=source,
        rows_read=len(frame),
        events=len(events),
        rows_out_of_window=out_of_window,
        rows_missing_timestamp=missing_timestamp,
        rows_incomplete_key=incomplete_key,
        rows_unknown_severity=unknown_severity,
    )
    return LoadedFeed(events=tuple(events), report=report)


def _optional_str(value: object) -> str | None:
    """Return `value` as a string, or `None` if the feed left the field blank."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _require_columns(frame: pd.DataFrame, columns: list[str], path: Path | str) -> None:
    """Fail loudly when an expected column is absent.

    A renamed column would otherwise surface much later as an empty result, by
    which point the cause is far from the symptom.
    """
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing expected column(s): {missing}")
