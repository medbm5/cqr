"""How much the answer depends on the two judgment calls behind it.

Two parameters in the frequency stage are conventions rather than measurements:
the severity at which an event counts as attack-grade, and the quiet period that
separates two attacks. Neither is derivable from the data, both move the answer,
and a single AAL quoted without them is a number the reader cannot argue with.

This grid re-runs the whole frequency-and-simulation chain across a range of each
and reports the AAL. It is the honest form of "how confident are you in that
figure": not a confidence interval, which would only describe sampling noise, but
the span of answers the defensible parameter choices produce.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from risk_engine.frequency import FrequencyParams, estimate_frequency
from risk_engine.ingestion import Asset, SecurityEvent, SeverityClass, TimeWindow
from risk_engine.severity import SeverityModel

from .engine import simulate

#: Severity thresholds swept by default: everything from Medium up, the standard
#: High, and only Critical.
DEFAULT_THRESHOLDS: tuple[SeverityClass, ...] = (
    SeverityClass.MEDIUM,
    SeverityClass.HIGH,
    SeverityClass.CRITICAL,
)

#: Session windows swept by default, in hours: a working day, a calendar day and
#: three days.
DEFAULT_SESSION_WINDOWS: tuple[float, ...] = (8.0, 24.0, 72.0)

#: Years per sensitivity cell. Lower than a headline run: nine cells at full
#: length would cost nine times a full simulation to answer a question about the
#: mean, which converges long before the tail does.
DEFAULT_SENSITIVITY_YEARS = 10_000


@dataclass(frozen=True, slots=True)
class SensitivityCell:
    """One point of the grid.

    Attributes:
        severity_threshold: The attack-grade threshold used.
        session_window_hours: The session gap used.
        episodes: Episodes the frequency stage found under those settings.
        lambda_total: The annualized attack rate that produced.
        aal: Average annual loss the simulation produced from it.
    """

    severity_threshold: SeverityClass
    session_window_hours: float
    episodes: int
    lambda_total: float
    aal: float


@dataclass(frozen=True, slots=True)
class SensitivityGrid:
    """AAL across a grid of frequency parameters.

    Attributes:
        cells: One cell per combination, threshold-major.
        thresholds: Severity thresholds swept.
        session_windows: Session windows swept, in hours.
        n_years: Years simulated per cell.
        seed: Seed shared by every cell, so differences between cells are the
            parameters and not the draws.
        baseline: The cell matching the headline run's parameters, when the sweep
            covers it.
    """

    cells: tuple[SensitivityCell, ...]
    thresholds: tuple[SeverityClass, ...]
    session_windows: tuple[float, ...]
    n_years: int
    seed: int
    baseline: SensitivityCell | None

    @property
    def aal_range(self) -> tuple[float, float]:
        """Lowest and highest AAL in the grid."""
        values = [cell.aal for cell in self.cells]
        return min(values), max(values)

    @property
    def spread_factor(self) -> float:
        """How many times larger the largest AAL is than the smallest.

        The number to quote when asked how robust the headline figure is.
        """
        low, high = self.aal_range
        return high / low if low > 0 else float("inf")

    def to_explanation(self) -> list[str]:
        """Render the grid as a numbered trace with a readable table."""
        lines = [
            f"1. Re-ran frequency and simulation across "
            f"{len(self.thresholds)}x{len(self.session_windows)} parameter "
            f"combinations, {self.n_years:,} year(s) each, all on seed {self.seed}.",
            "  threshold  window    episodes   lambda/yr              AAL",
        ]
        for cell in self.cells:
            marker = "  <- baseline" if cell == self.baseline else ""
            lines.append(
                f"  {cell.severity_threshold.value:9s} {cell.session_window_hours:>5.0f}h "
                f"{cell.episodes:>11,} {cell.lambda_total:>11,.1f} "
                f"EUR {cell.aal:>16,.0f}{marker}"
            )

        low, high = self.aal_range
        lines.append(
            f"2. AAL spans EUR {low:,.0f} to EUR {high:,.0f} across the grid, a factor "
            f"of {self.spread_factor:.1f}. That span is the cost of the two "
            f"conventions, and it is wider than any sampling error in the run."
        )
        return lines


def sensitivity_grid(
    events: Sequence[SecurityEvent],
    window: TimeWindow,
    severity: SeverityModel,
    *,
    assets: Sequence[Asset] = (),
    thresholds: Sequence[SeverityClass] = DEFAULT_THRESHOLDS,
    session_windows: Sequence[float] = DEFAULT_SESSION_WINDOWS,
    n_years: int = DEFAULT_SENSITIVITY_YEARS,
    seed: int = 42,
    baseline: FrequencyParams | None = None,
) -> SensitivityGrid:
    """Sweep the frequency conventions and report the AAL each produces.

    Only the frequency stage is re-run per cell; the severity model does not
    depend on telemetry parameters and is fitted once by the caller.

    Args:
        events: Canonical events from the ingestion stage.
        window: The observation window.
        severity: The fitted severity model, shared across cells.
        assets: Asset reference, passed through to the frequency stage.
        thresholds: Severity thresholds to sweep.
        session_windows: Session gaps to sweep, in hours.
        n_years: Years to simulate per cell.
        seed: Seed shared by every cell, so cells differ only by parameters.
        baseline: The headline run's parameters, marked in the output when the
            sweep covers them.

    Returns:
        The grid.
    """
    cells: list[SensitivityCell] = []
    marked: SensitivityCell | None = None

    for threshold in thresholds:
        for session_window in session_windows:
            params = FrequencyParams(severity_threshold=threshold, session_gap_hours=session_window)
            estimate = estimate_frequency(events, window, assets=assets, params=params)
            result = simulate(estimate, severity, n_years=n_years, seed=seed)

            cell = SensitivityCell(
                severity_threshold=threshold,
                session_window_hours=session_window,
                episodes=estimate.episodes,
                lambda_total=estimate.lambda_total,
                aal=result.metrics.aal,
            )
            cells.append(cell)
            if baseline is not None and params == baseline:
                marked = cell

    return SensitivityGrid(
        cells=tuple(cells),
        thresholds=tuple(thresholds),
        session_windows=tuple(session_windows),
        n_years=n_years,
        seed=seed,
        baseline=marked,
    )
