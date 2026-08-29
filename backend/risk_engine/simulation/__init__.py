"""Monte Carlo aggregation of frequency and severity into loss metrics.

Draws a Poisson event count per attack type for each simulated year, samples the
fitted severity for every incident, and sums to an annual loss. Ten thousand such
years are a distribution; a hundred thousand are a distribution with a readable
tail.

Every draw is vectorized across a block of years - there is no per-year Python
loop - and every source of randomness takes an explicit seed, so a run is
reproducible from `(seed, n_years)` alone.

Typical use::

    result = simulate(frequency, severity, n_years=100_000, seed=42)
    print(result.metrics.aal, result.metrics.var_99, result.metrics.tvar_99)

    for line in result.to_explanation():
        print(line)

`sensitivity_grid` re-runs the chain across the two frequency conventions that
are judgment calls rather than measurements, so the headline figure can be quoted
with the span of answers the defensible choices produce.
"""

from .engine import (
    DEFAULT_LOSS_CAP_QUANTILE,
    DEFAULT_N_YEARS,
    DRAWS_PER_BLOCK,
    HISTOGRAM_FLOOR_EUR,
    SimulationParams,
    SimulationResult,
    simulate,
)
from .metrics import (
    DEFAULT_EXCEEDANCE_PROBABILITIES,
    ExceedanceCurve,
    LossCap,
    LossHistogram,
    LossMetrics,
    exceedance_curve,
    log_spaced_probabilities,
    summarize,
)
from .sensitivity import (
    DEFAULT_SENSITIVITY_YEARS,
    DEFAULT_SESSION_WINDOWS,
    DEFAULT_THRESHOLDS,
    SensitivityCell,
    SensitivityGrid,
    sensitivity_grid,
)

__all__ = [
    "DEFAULT_EXCEEDANCE_PROBABILITIES",
    "DEFAULT_LOSS_CAP_QUANTILE",
    "DEFAULT_N_YEARS",
    "DEFAULT_SENSITIVITY_YEARS",
    "DEFAULT_SESSION_WINDOWS",
    "DEFAULT_THRESHOLDS",
    "DRAWS_PER_BLOCK",
    "HISTOGRAM_FLOOR_EUR",
    "ExceedanceCurve",
    "LossCap",
    "LossHistogram",
    "LossMetrics",
    "SensitivityCell",
    "SensitivityGrid",
    "SimulationParams",
    "SimulationResult",
    "exceedance_curve",
    "log_spaced_probabilities",
    "sensitivity_grid",
    "simulate",
    "summarize",
]
