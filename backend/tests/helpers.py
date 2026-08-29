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


def incident(
    incident_id="inc-1",
    *,
    sector="Retail",
    size="ETI",
    maturity=55.0,
    attack_type=None,
    loss=100_000.0,
    employees=1200,
):
    """Build one cleaned `Incident`, defaulting to an exact peer of the target."""
    from datetime import date as _date

    from risk_engine.attack_types import AttackType
    from risk_engine.severity.cleaning import Incident

    return Incident(
        incident_id=incident_id,
        company_id="ORG-1",
        occurred_on=_date(2024, 1, 15),
        sector=sector,
        company_size=size,
        employees=employees,
        attack_type=attack_type or AttackType.RANSOMWARE,
        severity="major",
        security_maturity_score=maturity,
        records_exposed=100.0,
        downtime_hours=5.0,
        loss_eur=loss,
    )
