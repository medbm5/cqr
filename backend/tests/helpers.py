"""Builders shared by the frequency tests.

Constructing a `SecurityEvent` takes seven arguments, most of which are noise for
any given test. These helpers let each test state only the thing it is about -
an offset, an asset, a technique or a severity.
"""

from datetime import UTC, datetime, timedelta

from risk_engine.ingestion import SecurityEvent, SeverityClass, Source

#: Instant every relative offset in the frequency tests is measured from.
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def event(
    offset_hours=0.0,
    *,
    asset="asset-1",
    technique="T1486",  # ransomware
    severity=SeverityClass.HIGH,
    event_id=None,
):
    """Build one canonical event at `offset_hours` past `BASE`."""
    return SecurityEvent(
        event_id=event_id or f"e-{offset_hours}-{asset}-{technique}",
        asset_id=asset,
        technique=technique,
        severity_score=None if severity is None else severity.score,
        severity_class=severity,
        observed_at=BASE + timedelta(hours=offset_hours),
        sources=(Source.SIEM,),
    )


def window(days):
    """A `TimeWindow` of `days` calendar days starting at `BASE`."""
    from risk_engine.ingestion import TimeWindow

    return TimeWindow(start=BASE, end=BASE + timedelta(days=days - 1), observed_days=days)
