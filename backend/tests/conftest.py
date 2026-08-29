"""Shared pytest fixtures.

Tests never touch the real CSVs in `data/`: every fixture is a small, readable
CSV under `tests/fixtures/` built to exercise one named edge case.
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory holding the small hand-written CSV fixtures."""
    return FIXTURES_DIR
