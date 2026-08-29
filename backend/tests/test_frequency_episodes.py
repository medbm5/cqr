"""Sessionization: turning bursts of alerts into countable attacks."""

import pytest
from helpers import event

from risk_engine.frequency import (
    AttackType,
    FrequencyParams,
    is_attack_grade,
    sessionize,
)
from risk_engine.ingestion import SeverityClass


def test_a_single_event_is_one_episode():
    episodes = sessionize([event()], params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 1
    assert episodes[0].started_at == episodes[0].ended_at
    assert episodes[0].duration_hours == 0.0
    assert episodes[0].attack_type is AttackType.RANSOMWARE


def test_gap_exactly_at_the_window_stays_one_episode():
    # The rule is "gap <= window_hours", so 24h apart is still one attack.
    episodes = sessionize([event(0), event(24)], params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 2
    assert episodes[0].duration_hours == 24.0


def test_gap_just_past_the_window_splits_the_episode():
    episodes = sessionize([event(0), event(24.001)], params=FrequencyParams())

    assert len(episodes) == 2
    assert all(episode.event_count == 1 for episode in episodes)


def test_the_gap_is_a_parameter():
    events = [event(0), event(5)]

    assert len(sessionize(events, params=FrequencyParams(session_gap_hours=8))) == 1
    assert len(sessionize(events, params=FrequencyParams(session_gap_hours=4))) == 2


def test_a_chain_of_short_gaps_is_one_long_episode():
    # Each step is under the window, so the whole run chains together even though
    # the first and last events are 60 hours apart.
    events = [event(hours) for hours in (0, 20, 40, 60)]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 4
    assert episodes[0].duration_hours == 60.0


def test_assets_are_sessionized_independently():
    events = [event(0, asset="asset-1"), event(1, asset="asset-2")]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 2
    assert {episode.asset_id for episode in episodes} == {"asset-1", "asset-2"}


def test_concurrent_attack_types_on_one_asset_are_separate_episodes():
    # A ransomware detection and a DDoS detection an hour apart are two attacks,
    # not one: the episode key is (asset, attack_type).
    events = [event(0, technique="T1486"), event(1, technique="T1498")]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 2
    assert {episode.attack_type for episode in episodes} == {
        AttackType.RANSOMWARE,
        AttackType.DDOS,
    }


def test_techniques_of_the_same_attack_type_share_an_episode():
    # T1486 and T1490 are both ransomware, so they belong to one attack.
    events = [event(0, technique="T1486"), event(1, technique="T1490")]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 2


def test_only_attack_grade_events_are_clustered():
    events = [
        event(0, severity=SeverityClass.LOW),
        event(1, severity=SeverityClass.MEDIUM),
        event(2, severity=SeverityClass.HIGH),
    ]

    episodes = sessionize(events, params=FrequencyParams())

    assert len(episodes) == 1
    assert episodes[0].event_count == 1


def test_the_severity_threshold_is_a_parameter():
    events = [event(0, severity=SeverityClass.MEDIUM), event(1, severity=SeverityClass.HIGH)]

    lenient = sessionize(events, params=FrequencyParams(severity_threshold=SeverityClass.MEDIUM))
    strict = sessionize(events, params=FrequencyParams(severity_threshold=SeverityClass.CRITICAL))

    assert len(lenient) == 1
    assert lenient[0].event_count == 2
    assert strict == ()


def test_ungraded_events_are_not_attack_grade():
    # An unknown grade is not evidence of a severe event, nor of a benign one.
    assert is_attack_grade(event(severity=None), SeverityClass.HIGH) is False
    assert sessionize([event(severity=None)], params=FrequencyParams()) == ()


def test_events_without_an_asset_cannot_be_clustered():
    assert sessionize([event(asset=None)], params=FrequencyParams()) == ()


def test_episode_records_its_peak_severity():
    events = [
        event(0, severity=SeverityClass.HIGH),
        event(1, severity=SeverityClass.CRITICAL),
        event(2, severity=SeverityClass.HIGH),
    ]

    episodes = sessionize(events, params=FrequencyParams())

    assert episodes[0].peak_severity is SeverityClass.CRITICAL


def test_output_is_sorted_and_independent_of_input_order():
    events = [event(hours) for hours in (0, 100, 50, 200)]

    forward = sessionize(events, params=FrequencyParams())
    backward = sessionize(list(reversed(events)), params=FrequencyParams())

    assert forward == backward
    starts = [episode.started_at for episode in forward]
    assert starts == sorted(starts)


def test_a_non_positive_gap_is_rejected():
    with pytest.raises(ValueError, match="must be positive"):
        FrequencyParams(session_gap_hours=0)
