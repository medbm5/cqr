"""Loading each feed into canonical events, and the per-feed accounting."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from risk_engine.ingestion import (
    SecurityEvent,
    SeverityClass,
    Source,
    TimeWindow,
    as_utc,
    load_assets,
    load_edr,
    load_siem,
    observed_window,
)


def test_load_assets_returns_typed_records(assets_csv):
    assets = load_assets(assets_csv)

    assert len(assets) == 2
    first = assets[0]
    assert first.asset_id == "asset-0001"
    assert first.asset_type == "server"
    assert first.business_criticality == 5
    assert isinstance(first.business_criticality, int)
    assert first.environment == "prod"


def test_load_assets_rejects_a_duplicate_identifier(tmp_path):
    path = tmp_path / "assets.csv"
    path.write_text(
        "asset_id,asset_type,business_criticality,environment\n"
        "asset-1,server,3,prod\n"
        "asset-1,database,4,prod\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate asset_id"):
        load_assets(path)


def test_load_assets_rejects_a_null_field(tmp_path):
    path = tmp_path / "assets.csv"
    path.write_text(
        "asset_id,asset_type,business_criticality,environment\nasset-1,server,,prod\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="null values"):
        load_assets(path)


def test_missing_column_is_reported_by_name(tmp_path):
    path = tmp_path / "assets.csv"
    path.write_text("asset_id,asset_type\nasset-1,server\n", encoding="utf-8")
    with pytest.raises(ValueError, match="business_criticality"):
        load_assets(path)


def test_load_siem_normalizes_severity_and_counts_what_it_kept(siem_csv):
    feed = load_siem(siem_csv)

    assert feed.report.source is Source.SIEM
    assert feed.report.rows_read == 7
    assert feed.report.events == 7
    # evt-6 has no asset_id, so it cannot take part in cross-feed matching.
    assert feed.report.rows_incomplete_key == 1
    # evt-4 has a blank severity: unknown, not Low.
    assert feed.report.rows_unknown_severity == 1

    by_id = {event.event_id: event for event in feed.events}
    assert by_id["evt-1"].severity_class is SeverityClass.HIGH
    assert by_id["evt-1"].severity_score == 0.75
    assert by_id["evt-1"].sources == (Source.SIEM,)
    assert by_id["evt-4"].severity_class is None
    assert by_id["evt-4"].severity_score is None
    assert by_id["evt-6"].asset_id is None
    assert by_id["evt-6"].has_dedup_key is False


def test_load_edr_applies_the_cut_points_and_flags_the_sentinel(edr_csv):
    feed = load_edr(edr_csv)

    assert feed.report.rows_read == 7
    assert feed.report.events == 7
    assert feed.report.rows_incomplete_key == 1  # edr-7 has no technique
    assert feed.report.rows_unknown_severity == 1  # edr-6 carries the 999 sentinel

    by_id = {event.event_id: event for event in feed.events}
    assert by_id["edr-4"].severity_class is SeverityClass.LOW  # risk 49
    assert by_id["edr-5"].severity_class is SeverityClass.MEDIUM  # risk 50
    assert by_id["edr-6"].severity_class is None  # risk 999
    assert by_id["edr-1"].severity_score == 1.0  # risk 95


def test_timestamps_are_returned_as_utc(siem_csv):
    feed = load_siem(siem_csv)

    for event in feed.events:
        assert event.observed_at.tzinfo is not None
        assert event.observed_at.utcoffset().total_seconds() == 0


def test_window_filters_rows_and_counts_the_exclusions(siem_csv):
    # The fixture spans 12:00 to 17:00 on 2026-01-01; keep only the first three hours.
    window = TimeWindow(
        start=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
        observed_days=1,
    )
    feed = load_siem(siem_csv, window=window)

    assert feed.report.rows_read == 7
    assert feed.report.events == 4  # evt-1, evt-2, evt-3, evt-5
    assert feed.report.rows_out_of_window == 3  # evt-4, evt-6, evt-7
    assert all(window.start <= event.observed_at <= window.end for event in feed.events)


def test_observed_window_is_derived_from_the_events(siem_csv, edr_csv):
    window = observed_window(load_siem(siem_csv).events, load_edr(edr_csv).events)

    assert window.start == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert window.end == datetime(2026, 1, 3, 12, 0, tzinfo=UTC)
    # Calendar days, inclusive of both ends: 1, 2 and 3 January.
    assert window.observed_days == 3
    assert window.annualization_factor == pytest.approx(365 / 3)


def test_observed_window_needs_at_least_one_event():
    with pytest.raises(ValueError, match="zero events"):
        observed_window([])


def test_as_utc_treats_a_naive_timestamp_as_utc():
    assert as_utc(datetime(2026, 1, 1, 12, 0)) == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_event_rejects_a_naive_timestamp():
    with pytest.raises(ValueError, match="timezone-aware"):
        SecurityEvent(
            event_id="e",
            asset_id="a",
            technique="T1",
            severity_score=0.25,
            severity_class=SeverityClass.LOW,
            observed_at=datetime(2026, 1, 1, 12, 0),
            sources=(Source.SIEM,),
        )


def test_event_rejects_a_half_set_severity():
    with pytest.raises(ValueError, match="both be set or both be None"):
        SecurityEvent(
            event_id="e",
            asset_id="a",
            technique="T1",
            severity_score=0.25,
            severity_class=None,
            observed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            sources=(Source.SIEM,),
        )


def test_rows_with_no_timestamp_are_dropped_and_counted(tmp_path):
    # A timeless detection can be neither windowed nor clustered into an episode,
    # so it is the one exclusion that removes the row entirely.
    path = tmp_path / "siem.csv"
    path.write_text(
        "event_id,asset_id,mitre_technique,severity,detected_at,source\n"
        "evt-1,asset-1,T1,High,2026-01-01T12:00:00,ids\n"
        "evt-2,asset-1,T2,Low,,ids\n",
        encoding="utf-8",
    )
    feed = load_siem(path)

    assert feed.report.rows_read == 2
    assert feed.report.events == 1
    assert feed.report.rows_missing_timestamp == 1


def test_edr_feed_with_a_null_risk_is_rejected(tmp_path):
    path = tmp_path / "edr.csv"
    path.write_text(
        "id,host,ttp,risk,timestamp\nedr-1,asset-1,T1,,2026-01-01 12:00:00\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no risk score"):
        load_edr(path)


def test_as_utc_converts_a_zoned_timestamp():
    paris_noon = datetime(2026, 1, 1, 13, 0, tzinfo=timezone(timedelta(hours=1)))
    assert as_utc(paris_noon) == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_event_requires_at_least_one_source():
    with pytest.raises(ValueError, match="at least one source"):
        SecurityEvent(
            event_id="e",
            asset_id="a",
            technique="T1",
            severity_score=0.25,
            severity_class=SeverityClass.LOW,
            observed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            sources=(),
        )


def test_dedup_key_refuses_an_incomplete_event():
    event = SecurityEvent(
        event_id="e",
        asset_id=None,
        technique="T1",
        severity_score=None,
        severity_class=None,
        observed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        sources=(Source.SIEM,),
    )
    assert event.has_dedup_key is False
    with pytest.raises(ValueError, match="no dedup key"):
        _ = event.dedup_key
