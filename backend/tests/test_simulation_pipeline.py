"""The sensitivity grid and the end-to-end CLI."""

import json

import pytest
from helpers import event, window
from test_severity_model import cleaning_report, population

from risk_engine.attack_types import AttackType
from risk_engine.frequency import FrequencyParams
from risk_engine.ingestion import SeverityClass
from risk_engine.severity import fit_severity_model
from risk_engine.simulation import sensitivity_grid


@pytest.fixture
def telemetry():
    """Attack-grade events spread over three assets, types and severities."""
    events = []
    for day in range(30):
        for index, (asset, technique, severity) in enumerate(
            [
                ("asset-1", "T1486", SeverityClass.CRITICAL),
                ("asset-1", "T1566", SeverityClass.HIGH),
                ("asset-2", "T1498", SeverityClass.MEDIUM),
                ("asset-3", "T1003", SeverityClass.HIGH),
            ]
        ):
            events.append(
                event(
                    day * 24 + index * 3,
                    asset=asset,
                    technique=technique,
                    severity=severity,
                    event_id=f"e-{day}-{index}",
                )
            )
    return events


@pytest.fixture
def severity():
    return fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report())


# ------------------------------------------------------------- sensitivity


def test_the_grid_covers_every_combination(telemetry, severity):
    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1)

    assert len(grid.cells) == 9
    assert len(grid.thresholds) == 3
    assert len(grid.session_windows) == 3
    assert len({(c.severity_threshold, c.session_window_hours) for c in grid.cells}) == 9


def test_a_looser_threshold_admits_more_attacks(telemetry, severity):
    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1)
    by_threshold = {
        threshold: [c for c in grid.cells if c.severity_threshold is threshold]
        for threshold in grid.thresholds
    }

    medium = max(c.lambda_total for c in by_threshold[SeverityClass.MEDIUM])
    critical = max(c.lambda_total for c in by_threshold[SeverityClass.CRITICAL])
    assert medium > critical


def test_a_wider_session_window_merges_more_episodes(telemetry, severity):
    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1)
    high = [c for c in grid.cells if c.severity_threshold is SeverityClass.HIGH]
    by_window = {c.session_window_hours: c.episodes for c in high}

    assert by_window[72.0] <= by_window[24.0] <= by_window[8.0]


def test_the_grid_reports_the_spread_it_found(telemetry, severity):
    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1)

    low, high = grid.aal_range
    assert low <= high
    assert grid.spread_factor == pytest.approx(high / low)


def test_the_baseline_cell_is_marked_when_the_sweep_covers_it(telemetry, severity):
    baseline = FrequencyParams(severity_threshold=SeverityClass.HIGH, session_gap_hours=24.0)

    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1, baseline=baseline)

    assert grid.baseline is not None
    assert grid.baseline.severity_threshold is SeverityClass.HIGH
    assert grid.baseline.session_window_hours == 24.0
    assert "<- baseline" in "\n".join(grid.to_explanation())


def test_the_baseline_is_absent_when_the_sweep_misses_it(telemetry, severity):
    baseline = FrequencyParams(severity_threshold=SeverityClass.HIGH, session_gap_hours=999.0)

    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1, baseline=baseline)

    assert grid.baseline is None


def test_the_grid_explains_itself(telemetry, severity):
    grid = sensitivity_grid(telemetry, window(30), severity, n_years=200, seed=1)
    text = "\n".join(grid.to_explanation())

    assert "3x3 parameter combinations" in text
    assert "threshold  window" in text
    assert "AAL spans EUR" in text


def test_spread_factor_is_infinite_when_a_cell_produces_no_loss(severity):
    # Only Critical events, so the Critical-threshold cells find attacks and the
    # others find none: one end of the range is zero.
    quiet = [event(0, severity=SeverityClass.LOW)]

    grid = sensitivity_grid(quiet, window(30), severity, n_years=100, seed=1)

    assert grid.aal_range == (0.0, 0.0)
    assert grid.spread_factor == float("inf")


# ---------------------------------------------------------------------- CLI


def test_the_cli_runs_the_whole_pipeline_into_one_document(tmp_path, fixtures_dir):
    from risk_engine.cli import main

    data_dir = fixtures_dir.parent.parent.parent / "data"
    if not (data_dir / "cyber_incidents.csv").exists():  # pragma: no cover
        pytest.skip("case data not present")

    out = tmp_path / "nested" / "results.json"
    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "--out",
            str(out),
            "--seed",
            "7",
            "--years",
            "500",
            "--sensitivity-years",
            "100",
            "--quiet",
        ]
    )

    assert exit_code == 0
    document = json.loads(out.read_text(encoding="utf-8"))

    assert document["parameters"] == {
        "seed": 7,
        "n_years": 500,
        "severity_threshold": "high",
        "session_gap_hours": 24.0,
    }
    # Every stage is present, with both its figures and its trace.
    for stage in ("ingestion", "frequency", "severity", "simulation", "sensitivity"):
        assert document[stage]["explanation"]

    assert document["ingestion"]["events_in_both_feeds"] == 12343
    assert document["frequency"]["lambda_total"] > 0
    assert document["severity"]["incidents_fitted"] == 1598
    assert document["simulation"]["metrics"]["aal_eur"] > 0
    assert (
        document["simulation"]["metrics"]["tvar_99_eur"]
        >= (document["simulation"]["metrics"]["var_99_eur"])
    )
    assert len(document["sensitivity"]["cells"]) == 9

    histogram = document["simulation"].get("histogram")
    assert histogram is None or len(histogram["bin_edges_eur"]) == len(histogram["counts"]) + 1

    curve = document["simulation"]["aep_curve"]
    assert curve["kind"] == "aep"
    assert len(curve["loss_eur"]) == len(curve["exceedance_probability"])


def test_the_cli_reports_a_missing_data_directory(tmp_path, capsys):
    from risk_engine.cli import main

    assert main(["--data-dir", str(tmp_path / "absent"), "--out", str(tmp_path / "r.json")]) == 1
    assert "data directory not found" in capsys.readouterr().err


def test_the_cli_reports_a_missing_input_file(tmp_path, capsys):
    from risk_engine.cli import main

    empty = tmp_path / "data"
    empty.mkdir()

    assert main(["--data-dir", str(empty), "--out", str(tmp_path / "r.json")]) == 1
    assert "error:" in capsys.readouterr().err


def test_the_cli_parser_defaults_match_the_documented_command():
    from risk_engine.cli import build_parser

    args = build_parser().parse_args([])

    assert str(args.data_dir) == "data"
    assert str(args.out) == "results.json"
    assert args.seed == 42
    assert args.years == 100_000
    assert args.sensitivity_years == 10_000


def test_every_cli_knob_is_overridable():
    from risk_engine.cli import build_parser

    args = build_parser().parse_args(
        ["--data-dir", "/elsewhere", "--out", "/tmp/r.json", "--seed", "7", "--years", "5"]
    )

    assert str(args.data_dir).endswith("elsewhere")
    assert args.seed == 7
    assert args.years == 5


def test_the_cli_prints_every_stage_unless_quietened(tmp_path, capsys, fixtures_dir):
    from risk_engine.cli import main

    data_dir = fixtures_dir.parent.parent.parent / "data"
    if not (data_dir / "cyber_incidents.csv").exists():  # pragma: no cover
        pytest.skip("case data not present")

    exit_code = main(
        [
            "--data-dir",
            str(data_dir),
            "--out",
            str(tmp_path / "results.json"),
            "--years",
            "200",
            "--sensitivity-years",
            "0",
        ]
    )

    assert exit_code == 0
    printed = capsys.readouterr().out
    for stage in ("ingestion", "frequency", "severity", "simulation"):
        assert f"=== {stage} ===" in printed
    # The grid was switched off, so it must not appear.
    assert "=== sensitivity ===" not in printed
    assert "wrote" in printed
