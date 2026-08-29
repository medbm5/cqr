"""Regression tests for the frequency stage.

Each one pins a property that was wrong, or could silently go wrong, in a way a
passing unit test elsewhere would not have caught. The λ guard at the end is the
only one that touches the real data, and it is a plausibility bound rather than
an assertion about a computed value.
"""

import pytest
from helpers import event, window

from risk_engine.frequency import (
    AttackType,
    FrequencyParams,
    estimate_frequency,
    sessionize,
)
from risk_engine.ingestion import SeverityClass

DAY = 24.0


# ------------------------------------------------------- clustering behaviour


def test_a_chain_of_daily_events_is_one_episode():
    """Ten events, each within 24h of its neighbour, spanning three days.

    The gap must be measured against the *previous* event in the run, not the
    run's first. Measuring against the first would cut this into four episodes
    the moment it passed 24h from the start.
    """
    events = [event(hours) for hours in (0, 8, 16, 24, 32, 40, 48, 56, 64, 72)]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 10
    assert episodes[0].duration_hours == 72.0


def test_different_techniques_on_one_asset_are_one_episode():
    """One asset, one hour, three techniques of three different attack types.

    An intruder on a machine trips whatever detections it has. Counting each
    technique - or each attack type - as its own attack counts the detections
    again under another name, which is what episodes exist to prevent.
    """
    events = [
        event(0.0, technique="T1486"),  # ransomware
        event(0.5, technique="T1566"),  # phishing
        event(1.0, technique="T1498"),  # ddos
    ]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 3


def test_a_mixed_episode_is_labelled_by_its_worst_event():
    events = [
        event(0.0, technique="T1566", severity=SeverityClass.HIGH),
        event(0.5, technique="T1486", severity=SeverityClass.CRITICAL),
        event(1.0, technique="T1498", severity=SeverityClass.HIGH),
    ]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].attack_type is AttackType.RANSOMWARE
    assert episodes[0].peak_severity is SeverityClass.CRITICAL


def test_only_high_and_critical_events_enter_clustering():
    """Low and medium are filtered out *before* bucketing, not after."""
    events = [
        event(0.0, severity=SeverityClass.LOW),
        event(1.0, severity=SeverityClass.MEDIUM),
        event(2.0, severity=SeverityClass.HIGH),
        event(3.0, severity=SeverityClass.CRITICAL),
        event(4.0, severity=None),
    ]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    # Only the HIGH and the CRITICAL, so the Low, Medium and ungraded events
    # never reached the cluster.
    assert episodes[0].event_count == 2
    assert episodes[0].started_at == event(2.0).observed_at


def test_separate_assets_never_share_an_episode():
    events = [event(0.0, asset="asset-1"), event(0.5, asset="asset-2")]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 2
    assert {episode.asset_id for episode in episodes} == {"asset-1", "asset-2"}


# ------------------------------------------------------------- the gap edge


def test_exactly_one_window_apart_is_one_episode():
    episodes = sessionize([event(0.0), event(DAY)], params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 2


def test_one_second_past_the_window_is_two_episodes():
    one_second = 1.0 / 3600.0
    episodes = sessionize([event(0.0), event(DAY + one_second)], params=FrequencyParams())

    assert len(episodes) == 2


# ----------------------------------------------------------- the calibration


def test_without_an_incident_base_the_estimate_stops_at_detection():
    estimate = estimate_frequency([event(0.0)], window(100))

    assert estimate.lambda_detected > 0
    assert estimate.calibration is None
    assert estimate.lambda_incident is None
    assert estimate.lambda_incident_by_attack_type is None
    assert "stops at detected attacks" in "\n".join(estimate.to_explanation())


def test_calibration_anchors_the_incident_rate_on_the_peer_base(fixtures_dir):
    """λ_incident is the peer base rate; λ_detected only sets p_materialize."""
    from risk_engine.severity import load_incidents

    path = fixtures_dir.parent.parent.parent / "data" / "cyber_incidents.csv"
    if not path.exists():  # pragma: no cover - data is not vendored everywhere
        pytest.skip("case data not present")
    incidents, _ = load_incidents(path)

    estimate = estimate_frequency([event(0.0)], window(365), incidents=incidents)
    calibration = estimate.calibration

    assert calibration is not None
    assert calibration.lambda_incident == pytest.approx(
        calibration.base_rate.incidents_per_company_year
    )
    assert calibration.p_materialize == pytest.approx(
        calibration.lambda_incident / calibration.lambda_detected
    )
    # The two rates are different units and must not be confused.
    assert calibration.lambda_incident < calibration.lambda_detected


def test_the_attack_type_mix_comes_from_the_telemetry(fixtures_dir):
    """The base rate sets *how often*; the telemetry sets *what kind*."""
    from risk_engine.severity import load_incidents

    path = fixtures_dir.parent.parent.parent / "data" / "cyber_incidents.csv"
    if not path.exists():  # pragma: no cover
        pytest.skip("case data not present")
    incidents, _ = load_incidents(path)

    events = [
        event(0.0, asset="asset-1", technique="T1486"),  # ransomware
        event(0.0, asset="asset-2", technique="T1486"),
        event(0.0, asset="asset-3", technique="T1566"),  # phishing
    ]
    estimate = estimate_frequency(events, window(365), incidents=incidents)
    mix = estimate.lambda_incident_by_attack_type

    assert mix is not None
    assert sum(mix.values()) == pytest.approx(estimate.lambda_incident)
    # Two of three episodes were ransomware, so it carries two thirds of the rate.
    assert mix[AttackType.RANSOMWARE] == pytest.approx(estimate.lambda_incident * 2 / 3)
    assert mix[AttackType.PHISHING] == pytest.approx(estimate.lambda_incident * 1 / 3)


# ------------------------------------------------------------ plausibility


def test_the_incident_rate_is_plausible_for_this_company(fixtures_dir):
    """A bound, not an assertion about a computed value.

    A 1,200-employee ETI does not suffer fewer than one loss-generating incident
    per twenty years, nor more than five per year. Anything outside that band
    means the frequency stage has lost track of its units again - which is
    exactly what happened when detected attacks were priced as incidents and the
    rate reached 9,168 per year.
    """
    from risk_engine.ingestion import load_assets, load_edr, load_siem, merge_feeds
    from risk_engine.severity import load_incidents

    data = fixtures_dir.parent.parent.parent / "data"
    if not (data / "cyber_incidents.csv").exists():  # pragma: no cover
        pytest.skip("case data not present")

    assets = load_assets(data / "asset_reference.csv")
    ingestion = merge_feeds(
        load_siem(data / "feed_siem.csv"), load_edr(data / "feed_edr.csv"), assets=assets
    )
    incidents, _ = load_incidents(data / "cyber_incidents.csv")

    estimate = estimate_frequency(
        ingestion.events,
        ingestion.report.window,
        assets=assets,
        incidents=incidents,
    )

    assert estimate.lambda_incident is not None
    assert 0.05 < estimate.lambda_incident < 5.0, (
        f"lambda_incident = {estimate.lambda_incident:.4f}/yr is outside the "
        f"plausible band for a 1,200-employee ETI"
    )
