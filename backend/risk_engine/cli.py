"""Standalone entry point for the risk engine pipeline.

Why a CLI: the engine must be reproducible without Django, without HTTP and
without a notebook kernel. ``python -m risk_engine --data-dir data/`` is the
reference way to regenerate ``results.json`` from the raw CSVs, so any number
displayed by the API or the frontend can be re-derived by a reviewer in one
command.

The JSON it writes carries both the figures and the numbered explanation behind
each stage, so the file is self-describing: nothing in it requires reading this
source to interpret.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from risk_engine import __version__
from risk_engine.frequency import FrequencyParams, estimate_frequency
from risk_engine.ingestion import load_assets, load_edr, load_siem, merge_feeds
from risk_engine.severity import fit_severity_model, load_incidents
from risk_engine.simulation import (
    DEFAULT_N_YEARS,
    DEFAULT_SENSITIVITY_YEARS,
    ExceedanceCurve,
    SimulationResult,
    sensitivity_grid,
    simulate,
)
from risk_engine.simulation.sensitivity import SensitivityGrid

DEFAULT_SEED = 42


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.

    Returns:
        The parser accepting the data directory, the output path, the seed and
        the simulation size.
    """
    parser = argparse.ArgumentParser(
        prog="risk-engine",
        description="Estimate the annualized cyber loss of the target company.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory holding the read-only input CSVs (default: ./data).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results.json"),
        help="Path of the JSON results file to write (default: ./results.json).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Seed for every random draw, so a run is reproducible (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=DEFAULT_N_YEARS,
        help=f"Years to simulate (default: {DEFAULT_N_YEARS:,}).",
    )
    parser.add_argument(
        "--sensitivity-years",
        type=int,
        default=DEFAULT_SENSITIVITY_YEARS,
        help=(
            f"Years to simulate per sensitivity cell "
            f"(default: {DEFAULT_SENSITIVITY_YEARS:,}; 0 skips the grid)."
        ),
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Write the results file without printing the explanations.",
    )
    return parser


def run_pipeline(
    data_dir: Path, *, seed: int, years: int, sensitivity_years: int
) -> dict[str, Any]:
    """Run every stage and assemble the results document.

    Args:
        data_dir: Directory holding the four input CSVs.
        seed: Seed for every random draw.
        years: Years to simulate for the headline figures.
        sensitivity_years: Years per sensitivity cell; zero skips the grid.

    Returns:
        A JSON-serializable document holding each stage's figures and its
        numbered explanation.
    """
    assets = load_assets(data_dir / "asset_reference.csv")
    ingestion = merge_feeds(
        load_siem(data_dir / "feed_siem.csv"),
        load_edr(data_dir / "feed_edr.csv"),
        assets=assets,
    )

    frequency_params = FrequencyParams()
    frequency = estimate_frequency(
        ingestion.events,
        ingestion.report.window,
        assets=assets,
        params=frequency_params,
        normalization=ingestion.report,
    )

    incidents, cleaning = load_incidents(data_dir / "cyber_incidents.csv")
    severity = fit_severity_model(incidents, cleaning)

    result = simulate(frequency, severity, n_years=years, seed=seed)

    grid: SensitivityGrid | None = None
    if sensitivity_years > 0:
        grid = sensitivity_grid(
            ingestion.events,
            ingestion.report.window,
            severity,
            assets=assets,
            n_years=sensitivity_years,
            seed=seed,
            baseline=frequency_params,
        )

    document: dict[str, Any] = {
        "engine_version": __version__,
        "inputs": {"data_dir": str(data_dir)},
        "parameters": {
            "seed": seed,
            "n_years": years,
            "severity_threshold": frequency_params.severity_threshold.value,
            "session_gap_hours": frequency_params.session_gap_hours,
        },
        "ingestion": {
            "rows_read": ingestion.report.rows_read,
            "events": ingestion.report.total_events,
            "events_in_both_feeds": ingestion.report.events_in_both_feeds,
            "duplicates_merged": ingestion.report.duplicates_merged,
            "inflation_avoided": ingestion.report.inflation_avoided,
            "window": {
                "start": ingestion.report.window.start.isoformat(),
                "end": ingestion.report.window.end.isoformat(),
                "observed_days": ingestion.report.window.observed_days,
                "annualization_factor": ingestion.report.window.annualization_factor,
            },
            "explanation": ingestion.to_explanation(),
        },
        "frequency": {
            "lambda_total": frequency.lambda_total,
            "lambda_by_attack_type": {
                attack_type.value: rate
                for attack_type, rate in frequency.lambda_by_attack_type.items()
            },
            "episodes": frequency.episodes,
            "episodes_by_attack_type": {
                attack_type.value: count
                for attack_type, count in frequency.episodes_by_attack_type.items()
            },
            "observed_days": frequency.observed_days,
            "episodes_by_criticality": {
                str(level): count for level, count in frequency.episodes_by_criticality.items()
            },
            "episodes_by_environment": dict(frequency.episodes_by_environment),
            "by_asset": [
                {
                    "asset_id": asset.asset_id,
                    "asset_type": asset.asset_type,
                    "business_criticality": asset.business_criticality,
                    "environment": asset.environment,
                    "episodes": asset.episodes,
                    "annual_rate": asset.annual_rate,
                }
                for asset in frequency.by_asset
            ],
            "explanation": frequency.to_explanation(),
        },
        "severity": {
            "incidents_total": severity.incidents_total,
            "incidents_fitted": severity.incidents_fitted,
            "min_effective_n": severity.min_effective_n,
            "peer_weighting": {
                "target_sector": severity.peer_params.target_sector,
                "target_size": severity.peer_params.target_size,
                "target_maturity": severity.peer_params.target_maturity,
                "sector_other_weight": severity.peer_params.sector_other_weight,
                "size_other_weight": severity.peer_params.size_other_weight,
                "maturity_bandwidth": severity.peer_params.maturity_bandwidth,
            },
            "by_attack_type": {
                attack_type.value: {
                    "mu": fit.params.mu,
                    "sigma": fit.params.sigma,
                    "median_eur": fit.params.median_eur,
                    "mean_eur": fit.params.mean_eur,
                    "observations": fit.own_observations,
                    "effective_n": fit.own_effective_n,
                    "used_pooled": fit.used_pooled,
                    "weighted_ks": fit.diagnostics.weighted_ks,
                    "qq_theoretical": list(fit.diagnostics.qq_theoretical),
                    "qq_empirical": list(fit.diagnostics.qq_empirical),
                    "pareto_tail": (
                        None
                        if fit.diagnostics.tail is None
                        else {
                            "threshold_eur": fit.diagnostics.tail.threshold_eur,
                            "alpha": fit.diagnostics.tail.alpha,
                            "exceedances": fit.diagnostics.tail.exceedances,
                            "ks_lognormal": fit.diagnostics.tail.ks_lognormal,
                            "ks_pareto": fit.diagnostics.tail.ks_pareto,
                            "pareto_fits_tail_better": (
                                fit.diagnostics.tail.pareto_fits_tail_better
                            ),
                        }
                    ),
                }
                for attack_type, fit in severity.fits.items()
            },
            "explanation": severity.to_explanation(),
        },
        "simulation": _simulation_document(result),
    }

    if grid is not None:
        document["sensitivity"] = {
            "n_years": grid.n_years,
            "seed": grid.seed,
            "aal_range_eur": list(grid.aal_range),
            "spread_factor": grid.spread_factor,
            "cells": [
                {
                    "severity_threshold": cell.severity_threshold.value,
                    "session_window_hours": cell.session_window_hours,
                    "episodes": cell.episodes,
                    "lambda_total": cell.lambda_total,
                    "aal": cell.aal,
                }
                for cell in grid.cells
            ],
            "explanation": grid.to_explanation(),
        }

    return document


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pipeline and write the results file.

    Args:
        argv: Command line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        A process exit code: ``0`` on success, ``1`` if the data directory is
        missing or incomplete.
    """
    args = build_parser().parse_args(argv)
    data_dir: Path = args.data_dir
    out_path: Path = args.out

    if not data_dir.is_dir():
        print(f"error: data directory not found: {data_dir}", file=sys.stderr)
        return 1

    try:
        document = run_pipeline(
            data_dir,
            seed=args.seed,
            years=args.years,
            sensitivity_years=args.sensitivity_years,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    if not args.quiet:
        for stage in ("ingestion", "frequency", "severity", "simulation", "sensitivity"):
            section = document.get(stage)
            if not isinstance(section, dict):
                continue
            print(f"\n=== {stage} ===")
            for line in section["explanation"]:
                print(line)

    print(f"\nwrote {out_path}")
    return 0


def _simulation_document(result: SimulationResult) -> dict[str, Any]:
    """Serialize the simulation stage."""
    metrics = result.metrics
    return {
        "n_years": result.params.n_years,
        "seed": result.params.seed,
        "metrics": {
            "aal_eur": metrics.aal,
            "median_eur": metrics.median,
            "var_95_eur": metrics.var_95,
            "var_99_eur": metrics.var_99,
            "tvar_95_eur": metrics.tvar_95,
            "tvar_99_eur": metrics.tvar_99,
            "probability_of_no_loss": metrics.probability_of_no_loss,
            "max_eur": metrics.maximum,
        },
        "expected_loss_by_attack_type": {
            attack_type.value: value for attack_type, value in result.expected_loss_by_type.items()
        },
        "expected_incidents_by_attack_type": {
            attack_type.value: value
            for attack_type, value in result.expected_incidents_by_type.items()
        },
        "aep_curve": _curve_document(result.aep),
        "oep_curve": _curve_document(result.oep),
        "explanation": result.to_explanation(),
    }


def _curve_document(curve: ExceedanceCurve) -> dict[str, Any]:
    """Serialize one exceedance curve as parallel plottable arrays."""
    return {
        "kind": curve.kind,
        "exceedance_probability": list(curve.exceedance_probability),
        "return_period_years": list(curve.return_period_years),
        "loss_eur": list(curve.loss_eur),
    }


if __name__ == "__main__":
    raise SystemExit(main())
