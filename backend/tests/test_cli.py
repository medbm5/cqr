"""Tests for the standalone pipeline entry point."""

import json
from pathlib import Path

from risk_engine import __version__
from risk_engine.cli import PIPELINE_STAGES, build_parser, main


def test_parser_defaults_are_repo_relative():
    args = build_parser().parse_args([])
    assert args.data == Path("data")
    assert args.out == Path("results.json")
    assert args.seed == 42


def test_seed_is_explicit_and_overridable():
    args = build_parser().parse_args(["--seed", "7"])
    assert args.seed == 7


def test_missing_data_directory_is_an_error(tmp_path, capsys):
    exit_code = main(["--data", str(tmp_path / "absent"), "--out", str(tmp_path / "r.json")])
    assert exit_code == 1
    assert "data directory not found" in capsys.readouterr().err


def test_run_writes_a_traceable_manifest(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out = tmp_path / "nested" / "results.json"

    assert main(["--data", str(data_dir), "--out", str(out), "--seed", "123"]) == 0

    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["engine_version"] == __version__
    assert manifest["inputs"]["data_dir"] == str(data_dir)
    assert manifest["parameters"]["seed"] == 123
    assert tuple(manifest["stages"]) == PIPELINE_STAGES
