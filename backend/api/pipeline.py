"""Cached access to the risk engine.

The dataset is four static CSVs. Reading them, deduplicating 45,840 rows and
fitting nine severity distributions takes a few seconds and produces the same
answer every time, so it happens once per process rather than once per request.

Nothing here decides anything. Every function is a memoized call into
`risk_engine`, which is what keeps the views thin and keeps the modeling
testable without an HTTP server.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from risk_engine.frequency import FrequencyEstimate, FrequencyParams, estimate_frequency
from risk_engine.ingestion import (
    Asset,
    IngestionResult,
    SeverityClass,
    TelemetrySummary,
    load_assets,
    load_edr,
    load_siem,
    merge_feeds,
    summarize_telemetry,
)
from risk_engine.severity import SeverityModel, fit_severity_model, load_incidents
from risk_engine.simulation import (
    DEFAULT_SENSITIVITY_YEARS,
    SensitivityGrid,
    SimulationResult,
    sensitivity_grid,
    simulate,
)

#: Simulation sizes the API will accept. A hundred thousand years takes about
#: half a minute, which is not a request; the cap keeps a single caller from
#: occupying a worker, and the cache makes a repeated request instant.
MIN_YEARS = 100
MAX_YEARS = 200_000
DEFAULT_YEARS = 25_000


@dataclass(frozen=True, slots=True)
class Dataset:
    """Everything derived from the static CSVs, loaded once.

    Attributes:
        assets: The asset reference.
        ingestion: Deduplicated events and the normalization report.
        telemetry: Weekly buckets and severity mix over the window.
        severity: The fitted severity model.
    """

    assets: tuple[Asset, ...]
    ingestion: IngestionResult
    telemetry: TelemetrySummary
    severity: SeverityModel


def data_dir() -> Path:
    """Directory the input CSVs are read from."""
    return Path(settings.RISK_ENGINE_DATA_DIR)


@lru_cache(maxsize=1)
def get_dataset() -> Dataset:
    """Load, normalize and fit everything that does not depend on a request.

    Returns:
        The cached dataset. Cleared by `reset_caches`.
    """
    directory = data_dir()
    assets = load_assets(directory / "asset_reference.csv")
    ingestion = merge_feeds(
        load_siem(directory / "feed_siem.csv"),
        load_edr(directory / "feed_edr.csv"),
        assets=assets,
    )
    incidents, cleaning = load_incidents(directory / "cyber_incidents.csv")
    return Dataset(
        assets=assets,
        ingestion=ingestion,
        telemetry=summarize_telemetry(ingestion.events),
        severity=fit_severity_model(incidents, cleaning),
    )


@lru_cache(maxsize=32)
def get_frequency(
    severity_threshold: SeverityClass = SeverityClass.HIGH,
    session_window_hours: float = 24.0,
) -> FrequencyEstimate:
    """Estimate frequency under one pair of conventions.

    Args:
        severity_threshold: Minimum severity for an event to count as an attack.
        session_window_hours: Quiet period that ends an episode.

    Returns:
        The cached estimate for those parameters.
    """
    dataset = get_dataset()
    return estimate_frequency(
        dataset.ingestion.events,
        dataset.ingestion.report.window,
        assets=dataset.assets,
        params=FrequencyParams(
            severity_threshold=severity_threshold, session_gap_hours=session_window_hours
        ),
        normalization=dataset.ingestion.report,
    )


@lru_cache(maxsize=16)
def get_simulation(
    n_years: int,
    seed: int,
    severity_threshold: SeverityClass = SeverityClass.HIGH,
    session_window_hours: float = 24.0,
) -> SimulationResult:
    """Run - or recall - one simulation.

    Args:
        n_years: Years to simulate.
        seed: Seed for every draw.
        severity_threshold: Frequency convention.
        session_window_hours: Frequency convention.

    Returns:
        The cached result for those arguments.
    """
    return simulate(
        get_frequency(severity_threshold, session_window_hours),
        get_dataset().severity,
        n_years=n_years,
        seed=seed,
    )


@lru_cache(maxsize=4)
def get_sensitivity(seed: int, n_years: int = DEFAULT_SENSITIVITY_YEARS) -> SensitivityGrid:
    """Run - or recall - the parameter sweep.

    Args:
        seed: Seed shared by every cell.
        n_years: Years per cell.

    Returns:
        The cached grid.
    """
    dataset = get_dataset()
    return sensitivity_grid(
        dataset.ingestion.events,
        dataset.ingestion.report.window,
        dataset.severity,
        assets=dataset.assets,
        n_years=n_years,
        seed=seed,
        baseline=FrequencyParams(),
    )


def reset_caches() -> None:
    """Forget everything cached. Used by tests that swap the data directory."""
    get_dataset.cache_clear()
    get_frequency.cache_clear()
    get_simulation.cache_clear()
    get_sensitivity.cache_clear()
