"""Annualization, attack-type segmentation and the per-asset breakdown."""

import pytest
from helpers import BASE, event, window

from risk_engine.frequency import (
    TECHNIQUE_TO_ATTACK_TYPE,
    UNOBSERVABLE_ATTACK_TYPES,
    AttackType,
    FrequencyParams,
    attack_type_for,
    estimate_frequency,
)
from risk_engine.ingestion import Asset, SeverityClass, TimeWindow

ASSETS = (
    Asset(asset_id="asset-1", asset_type="server", business_criticality=5, environment="prod"),
    Asset(asset_id="asset-2", asset_type="workstation", business_criticality=2, environment="dev"),
)


# --------------------------------------------------------------------------- mapping


def test_every_mapped_technique_targets_a_real_attack_type():
    assert all(isinstance(value, AttackType) for value in TECHNIQUE_TO_ATTACK_TYPE.values())


def test_unmapped_and_missing_techniques_fall_back_to_other():
    assert attack_type_for("T9999") is AttackType.OTHER
    assert attack_type_for(None) is AttackType.OTHER


def test_known_techniques_map_as_reviewed():
    assert attack_type_for("T1566") is AttackType.PHISHING
    assert attack_type_for("T1486") is AttackType.RANSOMWARE
    assert attack_type_for("T1003") is AttackType.CREDENTIAL_THEFT
    assert attack_type_for("T1498") is AttackType.DDOS


def test_the_telemetry_cannot_observe_supply_chain_or_insider_error():
    # Neither has an ATT&CK technique in the feeds. Recorded explicitly so a
    # lambda of zero is read as "unobservable", not as "no risk".
    assert (
        frozenset({AttackType.SUPPLY_CHAIN, AttackType.INSIDER_ERROR}) == UNOBSERVABLE_ATTACK_TYPES
    )
    assert not set(TECHNIQUE_TO_ATTACK_TYPE.values()) & UNOBSERVABLE_ATTACK_TYPES


# ----------------------------------------------------------------------- annualization


def test_annualization_scales_episodes_by_the_observed_window():
    # 2 episodes over 100 days -> 2 / 100 * 365.
    estimate = estimate_frequency([event(0), event(1000)], window(100))

    assert estimate.episodes == 2
    assert estimate.observed_days == 100
    assert estimate.lambda_total == pytest.approx(2 / 100 * 365)


def test_a_shorter_window_yields_a_higher_rate_for_the_same_episodes():
    events = [event(0), event(1000)]

    short = estimate_frequency(events, window(50))
    long = estimate_frequency(events, window(200))

    assert short.lambda_total == pytest.approx(4 * long.lambda_total)


def test_a_full_year_of_observation_leaves_the_count_unchanged():
    estimate = estimate_frequency([event(0)], window(365))

    assert estimate.lambda_total == pytest.approx(1.0)


def test_a_window_of_no_days_is_rejected():
    with pytest.raises(ValueError, match="at least one day"):
        estimate_frequency([event(0)], TimeWindow(start=BASE, end=BASE, observed_days=0))


def test_per_type_rates_sum_to_the_total():
    events = [event(0, technique="T1486"), event(0, technique="T1566"), event(0, technique="T1498")]

    estimate = estimate_frequency(events, window(100))

    assert sum(estimate.lambda_by_attack_type.values()) == pytest.approx(estimate.lambda_total)
    assert sum(estimate.episodes_by_attack_type.values()) == estimate.episodes


def test_every_attack_type_appears_even_at_zero():
    estimate = estimate_frequency([event(0, technique="T1486")], window(100))

    assert set(estimate.lambda_by_attack_type) == set(AttackType)
    assert estimate.lambda_by_attack_type[AttackType.SUPPLY_CHAIN] == 0.0
    assert estimate.lambda_by_attack_type[AttackType.RANSOMWARE] > 0.0


def test_unmapped_techniques_are_counted_as_other_and_reported():
    events = [event(0, technique="T9999"), event(1, technique="T9999")]

    estimate = estimate_frequency(events, window(100))

    assert estimate.episodes_by_attack_type[AttackType.OTHER] == 1
    assert estimate.unmapped_techniques == {"T9999": 2}


def test_a_null_technique_is_other_and_counted_separately():
    # There is no identifier to add to the mapping, so it cannot appear in
    # unmapped_techniques - but it still has to be accounted for, or "other"
    # holds more episodes than the report explains.
    estimate = estimate_frequency([event(0, technique=None)], window(100))

    assert estimate.episodes_by_attack_type[AttackType.OTHER] == 1
    assert estimate.unmapped_techniques == {}
    assert estimate.events_without_technique == 1
    assert "carried no technique at all" in "\n".join(estimate.to_explanation())


def test_other_is_fully_explained_by_its_two_causes():
    events = [
        event(0, technique=None),
        event(1, technique="T9999"),
        event(2, technique="T1486"),
    ]

    estimate = estimate_frequency(events, window(100))

    # Both causes contribute events, and the two counters together account for
    # every event that landed in "other".
    other_events = estimate.events_without_technique + sum(estimate.unmapped_techniques.values())
    assert other_events == 2
    # Those two events are on one asset an hour apart, so they are one attack.
    assert estimate.episodes_by_attack_type[AttackType.OTHER] == 1
    assert estimate.episodes_by_attack_type[AttackType.RANSOMWARE] == 1


# ------------------------------------------------------------------------- accounting


def test_the_estimate_counts_what_it_excluded():
    events = [
        event(0, severity=SeverityClass.HIGH),
        event(1, severity=SeverityClass.LOW),
        event(2, severity=None),
        event(3, asset=None, severity=SeverityClass.CRITICAL),
    ]

    estimate = estimate_frequency(events, window(100))

    assert estimate.events_total == 4
    assert estimate.events_attack_grade == 2  # the HIGH and the asset-less CRITICAL
    assert estimate.events_ungraded == 1
    assert estimate.events_without_asset == 1
    assert estimate.episodes == 1


def test_params_are_carried_on_the_estimate():
    params = FrequencyParams(severity_threshold=SeverityClass.CRITICAL, session_gap_hours=6)

    estimate = estimate_frequency([event(0)], window(10), params=params)

    assert estimate.params is params
    assert estimate.params.session_gap_hours == 6


# -------------------------------------------------------------------- asset breakdown


def test_per_asset_breakdown_joins_the_asset_reference():
    events = [
        event(0, asset="asset-1", technique="T1486"),
        event(100, asset="asset-1", technique="T1486"),
        event(0, asset="asset-2", technique="T1566"),
    ]

    estimate = estimate_frequency(events, window(100), assets=ASSETS)

    assert [asset.asset_id for asset in estimate.by_asset] == ["asset-1", "asset-2"]
    first = estimate.by_asset[0]
    assert first.episodes == 2
    assert first.business_criticality == 5
    assert first.environment == "prod"
    assert first.annual_rate == pytest.approx(2 / 100 * 365)
    assert first.episodes_by_attack_type == {AttackType.RANSOMWARE: 2}


def test_breakdown_aggregates_by_criticality_and_environment():
    events = [
        event(0, asset="asset-1", technique="T1486"),
        event(100, asset="asset-1", technique="T1486"),
        event(0, asset="asset-2", technique="T1566"),
    ]

    estimate = estimate_frequency(events, window(100), assets=ASSETS)

    assert estimate.episodes_by_criticality == {2: 1, 5: 2}
    assert estimate.episodes_by_environment == {"dev": 1, "prod": 2}


def test_an_asset_missing_from_the_reference_still_appears():
    estimate = estimate_frequency([event(0, asset="asset-unknown")], window(100), assets=ASSETS)

    only = estimate.by_asset[0]
    assert only.asset_id == "asset-unknown"
    assert only.business_criticality is None
    assert only.environment is None
    # It contributes episodes but cannot be grouped into the UI aggregates.
    assert estimate.episodes_by_criticality == {}


def test_breakdown_works_without_an_asset_reference():
    estimate = estimate_frequency([event(0)], window(100))

    assert estimate.by_asset[0].asset_type is None
    assert estimate.episodes_by_environment == {}


# ------------------------------------------------------------------------ explanation


def test_explanation_traces_events_through_to_lambda():
    events = [
        event(0, technique="T1486"),
        event(1, technique="T1486"),
        event(0, technique="T9999"),
        event(2, severity=None),
    ]

    lines = estimate_frequency(events, window(100)).to_explanation()
    text = "\n".join(lines)

    assert "Started from 4 unique event(s)." in text
    assert "no severity grade" in text
    assert "attack-grade event(s)" in text
    assert "Clustered them into 2 episode(s)" in text
    assert "/ 100 day(s) x 365" in text
    assert "T9999" in text
    assert "not observable from SIEM/EDR telemetry" in text

    numbered = [line for line in lines if not line.startswith("  ")]
    assert [line.split(".", 1)[0] for line in numbered] == [
        str(i) for i in range(1, len(numbered) + 1)
    ]


def test_explanation_starts_at_raw_rows_when_given_the_ingestion_report(siem_csv, edr_csv):
    from risk_engine.ingestion import load_edr, load_siem, merge_feeds

    result = merge_feeds(load_siem(siem_csv), load_edr(edr_csv))
    estimate = estimate_frequency(result.events, result.report.window, normalization=result.report)

    lines = estimate.to_explanation()
    assert lines[0].startswith("1. Read 14 raw row(s)")
    assert "Deduplicated to 10 unique event(s)" in "\n".join(lines)


def test_explanation_handles_an_estimate_with_no_events():
    estimate = estimate_frequency([], window(10))

    assert estimate.lambda_total == 0.0
    assert "Kept 0 attack-grade event(s)." in "\n".join(estimate.to_explanation())
