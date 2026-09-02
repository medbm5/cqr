#!/usr/bin/env python
"""Check that a deliverable archive holds what it should and nothing it should not.

`git archive` exports only tracked files, so the exclusions below are already
implied by `.gitignore`. This verifies them anyway: the archive is the thing that
actually gets emailed, and "it should be fine because git" is not a check.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

#: Path fragments that must never appear in the deliverable. Dependency trees and
#: build caches make an archive enormous and tell a reviewer nothing.
FORBIDDEN = (
    "node_modules/",
    ".venv/",
    "venv/",
    ".git/",
    "__pycache__/",
    ".next/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    ".ipynb_checkpoints/",
)

#: Files a colleague needs in order to pick the work up. Their absence means the
#: archive is incomplete regardless of how clean it is.
REQUIRED = (
    "README.md",
    "METHODOLOGY.md",
    "CONCEPTS.md",
    "logique_metier.pdf",
    "business_logic.pdf",
    "DEPLOYMENT.md",
    "next_steps.md",
    "PROMPTS.md",
    "Makefile",
    "backend/pyproject.toml",
    "backend/risk_engine/__init__.py",
    "backend/risk_engine/cli.py",
    "notebooks/01_eda.ipynb",
    "data/cyber_incidents.csv",
)


def verify(archive: Path) -> int:
    """Report on one archive.

    Args:
        archive: Path to the zip.

    Returns:
        `0` when the archive is complete and clean, `1` otherwise.
    """
    if not archive.exists():
        print(f"error: {archive} does not exist", file=sys.stderr)
        return 1

    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        size = sum(info.file_size for info in bundle.infolist())

    # Entries are prefixed with a top-level directory so the archive unpacks into
    # a folder rather than over the reviewer's working directory.
    stripped = [name.partition("/")[2] for name in names]

    offenders = sorted(
        {fragment for fragment in FORBIDDEN if any(fragment in name for name in names)}
    )
    missing = [required for required in REQUIRED if required not in stripped]

    print(f"{archive}: {len(names):,} entries, {size / 1_048_576:.1f} MB uncompressed")

    if offenders:
        print(
            f"  FAIL  archive contains excluded paths: {', '.join(offenders)}",
            file=sys.stderr,
        )
    else:
        print(f"  ok    none of the {len(FORBIDDEN)} excluded paths are present")

    if missing:
        print(f"  FAIL  archive is missing: {', '.join(missing)}", file=sys.stderr)
    else:
        print(f"  ok    all {len(REQUIRED)} required files are present")

    return 1 if offenders or missing else 0


def main(argv: list[str] | None = None) -> int:
    """Verify the archive named on the command line."""
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: verify_archive.py <archive.zip>", file=sys.stderr)
        return 1
    return verify(Path(arguments[0]))


if __name__ == "__main__":
    raise SystemExit(main())
