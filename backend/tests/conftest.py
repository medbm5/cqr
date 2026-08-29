"""Shared pytest fixtures.

Tests never touch the real CSVs in `data/`: every fixture is a small, readable
CSV under `tests/fixtures/` built to exercise one named edge case. The header
comments in those files spell out what each row is there to prove.
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory holding the small hand-written CSV fixtures."""
    return FIXTURES_DIR


@pytest.fixture
def siem_csv() -> Path:
    """A seven-row SIEM export covering merge, repeat, blank grade and unknown asset."""
    return FIXTURES_DIR / "feed_siem_small.csv"


@pytest.fixture
def edr_csv() -> Path:
    """A seven-row EDR export covering cut-point edges, the sentinel and a null technique."""
    return FIXTURES_DIR / "feed_edr_small.csv"


@pytest.fixture
def assets_csv() -> Path:
    """A two-row asset reference; the telemetry references a third, unknown asset."""
    return FIXTURES_DIR / "assets_small.csv"
