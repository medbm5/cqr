"""Cached access to the risk engine.

The dataset is four static CSVs. Reading them, deduplicating 45,840 rows and
fitting nine severity distributions takes a few seconds and produces the same
answer every time, so it happens once per process rather than once per request.

Nothing here decides anything. Every function is a memoized call into
`risk_engine`, which is what keeps the views thin and keeps the modeling
testable without an HTTP server.
"""

from __future__ import annotations

import logging
import os
import threading
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
    SensitivityGrid,
    SimulationResult,
    sensitivity_grid,
    simulate,
)


#: Simulation sizes the API will accept. A hundred thousand years takes about
#: half a minute, which is not a request; the cap keeps a single caller from
#: occupying a worker, and the cache makes a repeated request instant.
def _env_int(name: str, default: int) -> int:
    """Read an integer environment override, falling back to the default."""
    raw = os.environ.get(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


MIN_YEARS = 100

#: Simulation sizes the API will accept and serve by default.
#:
#: Sized for the instance, not for the model. Measured on a Render free tier at
#: roughly 4.2 ms per simulated year - about fourteen times slower than a
#: workstation - so the 25,000-year default and its 9 x 10,000-year sensitivity
#: grid needed some eight minutes of CPU and never survived the gateway timeout.
#: Five thousand years plus a 9 x 1,000 grid is about a minute, which the
#: background warm-up absorbs before anyone asks for it.
#:
#: Both are environment overrides so a larger instance can raise them without a
#: rebuild, and the CLI - which has a whole machine to itself - is untouched at
#: 100,000 years.
MAX_YEARS = _env_int("RISK_ENGINE_MAX_YEARS", 200_000)
DEFAULT_YEARS = _env_int("RISK_ENGINE_DEFAULT_YEARS", 5_000)
DEFAULT_GRID_YEARS = _env_int("RISK_ENGINE_SENSITIVITY_YEARS", 1_000)

#: The default request, in one place.
#:
#: These matter more than they look. `lru_cache` keys on the *call*, not on the
#: resolved arguments, so `get_simulation(25_000, 42)` and
#: `get_simulation(25_000, 42, SeverityClass.HIGH, 24.0)` are two different
#: entries computing the same answer. Warming one and serving the other means
#: warming a key nothing will ever hit - which is exactly what happened the first
#: time this was measured in a container: 21s on the first request despite a
#: "warm start complete" in the log.
#:
#: The cached functions below therefore take no defaults at all, so every caller
#: is explicit and no two spellings of the same request can diverge.
DEFAULT_SEED = 42
DEFAULT_THRESHOLD = SeverityClass.HIGH
DEFAULT_WINDOW_HOURS = 24.0

logger = logging.getLogger(__name__)

#: Serializes the warm-up against the first real request. Without it both would
#: compute the same simulation at once - correct, because `lru_cache` would keep
#: one, but twice the peak memory on an instance chosen for being small.
_warm_lock = threading.Lock()


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


@lru_cache(maxsize=8)
def get_frequency(
    severity_threshold: SeverityClass,
    session_window_hours: float,
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


# Each entry retains two float64 arrays of n_years, so at the 200,000-year cap
# four entries is about 13 MB. Sixteen was 51 MB of results nobody had asked
# for twice.
@lru_cache(maxsize=4)
def get_simulation(
    n_years: int,
    seed: int,
    severity_threshold: SeverityClass,
    session_window_hours: float,
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
def get_sensitivity(seed: int, n_years: int) -> SensitivityGrid:
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


def warm_start() -> None:
    """Load the dataset and run the default simulation before any request.

    Reading four CSVs, deduplicating 45,840 rows and fitting nine severity
    distributions takes a few seconds; the default simulation takes a few more.
    Doing it at boot means the first visitor reads a warm cache instead of
    paying for the cold one.

    Failures are logged and swallowed. A warm-up is an optimisation, and a
    service that refuses to start because it could not pre-compute an
    optimisation is worse than one that starts cold.
    """
    with _warm_lock:
        try:
            get_dataset()
            # Exactly the call the view makes for a default request, argument for
            # argument - including the sensitivity grid, which a default POST
            # asks for and which costs nine more simulations.
            get_simulation(DEFAULT_YEARS, DEFAULT_SEED, DEFAULT_THRESHOLD, DEFAULT_WINDOW_HOURS)
            get_sensitivity(DEFAULT_SEED, DEFAULT_GRID_YEARS)
        except Exception:
            logger.exception("warm start failed; the first request will pay for it")
        else:
            logger.info(
                "warm start complete: dataset loaded, %s-year simulation and the "
                "sensitivity grid cached",
                f"{DEFAULT_YEARS:,}",
            )


def reset_caches() -> None:
    """Forget everything cached. Used by tests that swap the data directory."""
    get_dataset.cache_clear()
    get_frequency.cache_clear()
    get_simulation.cache_clear()
    get_sensitivity.cache_clear()
