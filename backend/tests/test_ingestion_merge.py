"""Cross-feed deduplication: the behaviour the whole stage exists for."""

from datetime import UTC, datetime

import pytest

from risk_engine.ingestion import (
    FeedReport,
    LoadedFeed,
    NormalizationReport,
    SecurityEvent,
    SeverityClass,
    Source,
    TimeWindow,
    load_assets,
    load_edr,
    load_siem,
    merge_feeds,
)


@pytest.fixture
def result(siem_csv, edr_csv, assets_csv):
    """The merged fixture feeds, with the asset reference attached."""
    return merge_feeds(load_siem(siem_csv), load_edr(edr_csv), assets=load_assets(assets_csv))


@pytest.fixture
def by_id(result):
    """Merged events keyed by their canonical event id."""
    return {event.event_id: event for event in result.events}


def test_duplicates_collapse_into_distinct_events(result):
    # 7 SIEM + 7 EDR rows describe 10 distinct events: three pairs match across
    # feeds, one pair repeats inside the SIEM, and two rows have incomplete keys.
    assert result.report.total_events == 10
    assert result.report.duplicates_merged == 4
    assert result.report.events_in_both_feeds == 3
    assert len(result.events) == 10


def test_naive_concatenation_would_have_inflated_the_count(result):
    assert result.report.inflation_avoided == pytest.approx(14 / 10 - 1)


def test_merged_event_keeps_both_sources_and_the_worst_severity(by_id):
    # evt-1 was graded High by the SIEM; the EDR scored the same detection 95,
    # which maps to Critical. The worse signal is the one a defender must act on.
    merged = by_id["evt-1"]
    assert merged.sources == (Source.SIEM, Source.EDR)
    assert merged.severity_class is SeverityClass.CRITICAL
    assert merged.severity_score == 1.0


def test_worst_severity_wins_in_the_other_direction_too(by_id):
    # evt-3 is Critical in the SIEM; the EDR scored it 10 (Low). The SIEM grade wins.
    merged = by_id["evt-3"]
    assert merged.sources == (Source.SIEM, Source.EDR)
    assert merged.severity_class is SeverityClass.CRITICAL


def test_unknown_severity_never_beats_a_known_grade(by_id):
    # evt-4 has a blank SIEM severity; the EDR scored it 80 (High). An unknown
    # grade carries no information, so the known one is adopted.
    merged = by_id["evt-4"]
    assert merged.sources == (Source.SIEM, Source.EDR)
    assert merged.severity_class is SeverityClass.HIGH


def test_severity_stays_unknown_when_no_feed_graded_it(by_id):
    # edr-6 carries the 999 sentinel and appears in no other feed.
    assert by_id["edr-6"].severity_class is None
    assert by_id["edr-6"].severity_score is None


def test_repeats_within_a_single_feed_also_collapse(by_id):
    # evt-2 and evt-5 share (asset-0001, T1002, 13:00). Both are SIEM rows, so
    # the merged event keeps one source and the worse of the two grades.
    merged = by_id["evt-2"]
    assert merged.sources == (Source.SIEM,)
    assert merged.severity_class is SeverityClass.MEDIUM
    assert "evt-5" not in by_id


def test_events_with_an_incomplete_key_are_carried_never_matched(by_id):
    # evt-6 has no asset and edr-7 has no technique. Neither can be compared to
    # anything, so both survive as distinct events rather than being dropped.
    assert by_id["evt-6"].asset_id is None
    assert by_id["evt-6"].sources == (Source.SIEM,)
    assert by_id["edr-7"].technique is None
    assert by_id["edr-7"].sources == (Source.EDR,)


def test_unknown_assets_are_flagged_and_kept(result, by_id):
    # evt-7 references asset-0009, which the two-row reference does not contain.
    assert result.report.unknown_asset_ids == ("asset-0009",)
    assert result.report.events_on_unknown_assets == 1
    assert by_id["evt-7"].asset_id == "asset-0009"


def test_unknown_assets_are_not_reported_without_a_reference(siem_csv, edr_csv):
    result = merge_feeds(load_siem(siem_csv), load_edr(edr_csv))

    assert result.report.unknown_asset_ids == ()
    assert result.report.events_on_unknown_assets == 0


def test_window_is_derived_from_the_merged_events(result):
    window = result.report.window
    assert window.start == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert window.end == datetime(2026, 1, 3, 12, 0, tzinfo=UTC)
    assert window.observed_days == 3


def test_events_are_sorted_and_the_result_is_order_independent(siem_csv, edr_csv, assets_csv):
    """Merging is a set operation, so shuffled input must give an identical result."""
    siem, edr, assets = load_siem(siem_csv), load_edr(edr_csv), load_assets(assets_csv)
    forward = merge_feeds(siem, edr, assets=assets)

    reversed_siem = type(siem)(events=tuple(reversed(siem.events)), report=siem.report)
    reversed_edr = type(edr)(events=tuple(reversed(edr.events)), report=edr.report)
    backward = merge_feeds(reversed_siem, reversed_edr, assets=assets)

    assert forward.events == backward.events
    ordering = [(event.observed_at, event.event_id) for event in forward.events]
    assert ordering == sorted(ordering)


def test_row_accounting_adds_up(result):
    """Every row read is either an emitted event or an explained exclusion."""
    for feed in result.report.feeds:
        assert feed.rows_read == feed.events + feed.rows_out_of_window + feed.rows_missing_timestamp

    emitted = sum(feed.events for feed in result.report.feeds)
    assert emitted - result.report.duplicates_merged == result.report.total_events


def test_explanation_traces_the_run_in_order(result):
    lines = result.to_explanation()
    text = "\n".join(lines)

    assert lines[0].startswith("1. Read 7 rows from the SIEM feed.")
    assert "Read 7 rows from the EDR feed." in text
    assert "collapsed to 10 distinct event(s)" in text
    assert "seen by both feeds" in text
    assert "worse grade was kept" in text
    assert "asset-0009" in text
    assert "365 / 3" in text
    # Top-level steps are numbered; detail lines are indented under them.
    numbered = [line for line in lines if not line.startswith("  ")]
    assert [line.split(".", 1)[0] for line in numbered] == [
        str(i) for i in range(1, len(numbered) + 1)
    ]


def _feed(source, *events):
    """Wrap hand-built events as a LoadedFeed, for cases the CSV fixtures don't reach."""
    return LoadedFeed(
        events=events,
        report=FeedReport(source=source, rows_read=len(events), events=len(events)),
    )


def _event(event_id, source, severity, minute=0):
    return SecurityEvent(
        event_id=event_id,
        asset_id="asset-1",
        technique="T1",
        severity_score=None if severity is None else severity.score,
        severity_class=severity,
        observed_at=datetime(2026, 1, 1, 12, minute, tzinfo=UTC),
        sources=(source,),
    )


def test_a_known_grade_survives_an_unknown_arriving_second():
    # The mirror of the fixture case: here the SIEM graded the event and the EDR
    # emitted its sentinel. The known grade must still win.
    siem = _feed(Source.SIEM, _event("evt-1", Source.SIEM, SeverityClass.HIGH))
    edr = _feed(Source.EDR, _event("edr-1", Source.EDR, None))

    merged = merge_feeds(siem, edr).events[0]

    assert merged.severity_class is SeverityClass.HIGH
    assert merged.sources == (Source.SIEM, Source.EDR)
    assert merged.event_id == "evt-1"


def test_two_unknown_grades_stay_unknown():
    siem = _feed(Source.SIEM, _event("evt-1", Source.SIEM, None))
    edr = _feed(Source.EDR, _event("edr-1", Source.EDR, None))

    merged = merge_feeds(siem, edr).events[0]

    assert merged.severity_class is None
    assert merged.severity_score is None


def test_report_totals_rows_across_feeds(result):
    assert result.report.rows_read == 14


def test_inflation_is_zero_when_nothing_was_read():
    empty = NormalizationReport(
        feeds=(),
        window=TimeWindow(
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 1, 1, tzinfo=UTC),
            observed_days=1,
        ),
        duplicates_merged=0,
        events_in_both_feeds=0,
        total_events=0,
    )
    assert empty.inflation_avoided == 0.0


def test_explanation_reports_dropped_rows(siem_csv):
    window = TimeWindow(
        start=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        end=datetime(2026, 1, 1, 14, 0, tzinfo=UTC),
        observed_days=1,
    )
    siem = load_siem(siem_csv, window=window)
    edr = _feed(Source.EDR, _event("edr-1", Source.EDR, SeverityClass.LOW, minute=30))

    text = "\n".join(merge_feeds(siem, edr, window=window).to_explanation())

    assert "Dropped 3 row(s) outside the requested observation window." in text


def test_explanation_reports_rows_dropped_for_a_missing_timestamp():
    events = (_event("evt-1", Source.SIEM, SeverityClass.LOW),)
    siem = LoadedFeed(
        events=events,
        report=FeedReport(source=Source.SIEM, rows_read=2, events=1, rows_missing_timestamp=1),
    )
    edr = _feed(Source.EDR)

    text = "\n".join(merge_feeds(siem, edr).to_explanation())

    assert "Dropped 1 row(s) with no usable timestamp" in text
