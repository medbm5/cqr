"""Standalone entry point for the risk engine pipeline.

Why a CLI: the engine must be reproducible without Django, without HTTP and
without a notebook kernel. ``python -m risk_engine.cli`` is the reference way to
regenerate ``results.json`` from the raw CSVs, so any number displayed by the
API or the frontend can be re-derived by a reviewer in one command.

At this stage the pipeline stages are not implemented; the CLI emits a run
manifest recording exactly which inputs, parameters and seed a run was launched
with. Each stage fills in its own section as it lands.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from risk_engine import __version__

#: Pipeline stages, in execution order. Each one will publish a section of
#: ``results.json`` under its own key.
PIPELINE_STAGES: tuple[str, ...] = (
    "ingestion",
    "frequency",
    "severity",
    "simulation",
)

DEFAULT_SEED = 42


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.

    Returns:
        The parser accepting the data directory, the output path and the seed.
    """
    parser = argparse.ArgumentParser(
        prog="risk-engine",
        description="Estimate the annualized cyber loss of the target company.",
    )
    parser.add_argument(
        "--data",
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
    return parser


def build_manifest(data_dir: Path, seed: int) -> dict[str, Any]:
    """Describe the run so its outputs stay traceable to their inputs.

    Args:
        data_dir: Directory the raw CSVs are read from.
        seed: Seed handed to every random draw of the run.

    Returns:
        A JSON-serializable manifest: engine version, inputs, seed and the
        per-stage status of the pipeline.
    """
    return {
        "engine_version": __version__,
        "inputs": {"data_dir": str(data_dir)},
        "parameters": {"seed": seed},
        "stages": {stage: {"status": "not_implemented"} for stage in PIPELINE_STAGES},
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pipeline and write the results file.

    Args:
        argv: Command line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        A process exit code: ``0`` on success, ``1`` if the data directory is
        missing.
    """
    args = build_parser().parse_args(argv)
    data_dir: Path = args.data
    out_path: Path = args.out

    if not data_dir.is_dir():
        print(f"error: data directory not found: {data_dir}", file=sys.stderr)
        return 1

    manifest = build_manifest(data_dir, args.seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path} (no stage implemented yet)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
