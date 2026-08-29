"""Risk metrics and exceedance curves read off a simulated loss distribution."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

Floats = npt.NDArray[np.float64]

#: Exceedance probabilities the curves are evaluated at, from a 1-in-2-year loss
#: down to a 1-in-10,000-year loss. Denser at the tail, where the curve bends and
#: where the decisions are made.
DEFAULT_EXCEEDANCE_PROBABILITIES: tuple[float, ...] = (
    0.5,
    0.4,
    0.3,
    0.2,
    0.1,
    0.05,
    0.04,
    0.02,
    0.01,
    0.005,
    0.004,
    0.002,
    0.001,
    0.0005,
    0.0002,
    0.0001,
)


@dataclass(frozen=True, slots=True)
class LossMetrics:
    """Summary of one simulated annual-loss distribution.

    Attributes:
        aal: Average annual loss - the mean of the simulated years. The figure a
            budget is set from, and the one most distorted by the tail.
        median: The loss a typical year brings. Far below the AAL whenever the
            distribution is heavy-tailed, which is why both are reported.
        var_95: 95th percentile of annual loss. The loss a 1-in-20 year reaches.
        var_99: 99th percentile. The loss a 1-in-100 year reaches.
        tvar_95: Mean annual loss across the worst 5% of years. Always at least
            `var_95`: it averages the losses beyond that point instead of naming
            the point itself, so it says how bad a bad year gets rather than only
            how often one arrives.
        tvar_99: Mean annual loss across the worst 1% of years.
        probability_of_no_loss: Share of simulated years with no loss at all.
        maximum: Worst single year in the simulation. A sample maximum, not an
            estimate of the worst possible year - run more years and it grows.
    """

    aal: float
    median: float
    var_95: float
    var_99: float
    tvar_95: float
    tvar_99: float
    probability_of_no_loss: float
    maximum: float


@dataclass(frozen=True, slots=True)
class ExceedanceCurve:
    """A loss-versus-probability curve, ready to plot.

    Attributes:
        kind: `"aep"` or `"oep"`, see below.
        exceedance_probability: Annual probability of exceeding the paired loss,
            descending - so the curve reads left to right from common to rare.
        loss_eur: The loss exceeded with that probability.
        return_period_years: `1 / exceedance_probability`, the same information
            in the units underwriters use.

    **AEP - Aggregate Exceedance Probability.** The probability that the *total*
    of all losses in a year exceeds a given amount. This is the curve for
    questions about annual budget and capital: a year with three €2M incidents
    hits €6M on the AEP curve.

    **OEP - Occurrence Exceedance Probability.** The probability that the
    *largest single* loss in a year exceeds a given amount. This is the curve for
    questions about per-incident limits and deductibles: that same year hits only
    €2M on the OEP curve, because no one incident cost more.

    OEP never exceeds AEP at a given probability, since the largest loss of a
    year is at most that year's total.
    """

    kind: str
    exceedance_probability: tuple[float, ...]
    loss_eur: tuple[float, ...]
    return_period_years: tuple[float, ...]


def log_spaced_probabilities(points: int, *, finest: float) -> tuple[float, ...]:
    """Exceedance probabilities spaced evenly on a log scale.

    A dense curve for plotting. Log spacing puts as many points across the rare
    tail as across the common body, which is where an exceedance curve carries
    its information - linear spacing would spend nearly every point between a
    1-in-2 and a 1-in-3 year.

    Args:
        points: How many probabilities to return.
        finest: The rarest probability to include, normally `1 / n_years`.

    Returns:
        Probabilities descending from 0.5 to `finest`.

    Raises:
        ValueError: If `points` is below 2, or `finest` is outside (0, 0.5].
    """
    if points < 2:
        raise ValueError(f"points must be at least 2, got {points}")
    if not 0.0 < finest <= 0.5:
        raise ValueError(f"finest must be in (0, 0.5], got {finest}")

    exponents = np.linspace(np.log10(0.5), np.log10(finest), points)
    values = np.power(10.0, exponents)
    # Pin the endpoints: raising 10 to a rounded logarithm lands a hair either
    # side of the target, and a `finest` a hair too small is dropped by
    # `exceedance_curve` as unresolvable, silently costing the last point.
    values[0], values[-1] = 0.5, finest
    return tuple(float(value) for value in values)


def summarize(annual_losses: Floats) -> LossMetrics:
    """Reduce a simulated loss distribution to its headline metrics.

    Args:
        annual_losses: One total loss per simulated year.

    Returns:
        The metrics. `tvar_95 >= var_95` and `tvar_99 >= var_99` hold by
        construction, and are asserted in the tests as a guard against a
        quantile convention slipping.

    Raises:
        ValueError: If no years were simulated.
    """
    if annual_losses.size == 0:
        raise ValueError("cannot summarize zero simulated years")

    var_95 = float(np.quantile(annual_losses, 0.95))
    var_99 = float(np.quantile(annual_losses, 0.99))
    return LossMetrics(
        aal=float(annual_losses.mean()),
        median=float(np.median(annual_losses)),
        var_95=var_95,
        var_99=var_99,
        tvar_95=_tail_mean(annual_losses, var_95),
        tvar_99=_tail_mean(annual_losses, var_99),
        probability_of_no_loss=float(np.mean(annual_losses <= 0.0)),
        maximum=float(annual_losses.max()),
    )


def exceedance_curve(
    losses: Floats,
    *,
    kind: str,
    probabilities: tuple[float, ...] = DEFAULT_EXCEEDANCE_PROBABILITIES,
) -> ExceedanceCurve:
    """Build an exceedance curve from a simulated per-year series.

    Args:
        losses: One value per simulated year - the annual total for an AEP curve,
            the annual largest single loss for an OEP curve.
        kind: `"aep"` or `"oep"`, recorded on the curve.
        probabilities: Exceedance probabilities to evaluate.

    Returns:
        The curve. Probabilities finer than the simulation can resolve - below
        `1 / n_years` - are dropped rather than reported as a number the run
        cannot support.

    Raises:
        ValueError: If no years were simulated, or `kind` is not aep or oep.
    """
    if losses.size == 0:
        raise ValueError("cannot build an exceedance curve from zero simulated years")
    if kind not in {"aep", "oep"}:
        raise ValueError(f"kind must be 'aep' or 'oep', got {kind!r}")

    resolvable = tuple(p for p in probabilities if p >= 1.0 / losses.size)
    quantiles = np.quantile(losses, [1.0 - p for p in resolvable])
    return ExceedanceCurve(
        kind=kind,
        exceedance_probability=resolvable,
        loss_eur=tuple(float(value) for value in np.atleast_1d(quantiles)),
        return_period_years=tuple(1.0 / p for p in resolvable),
    )


def _tail_mean(annual_losses: Floats, threshold: float) -> float:
    """Mean of the losses at or above `threshold`.

    `threshold` is always a quantile of `annual_losses`, so the selection is
    never empty - the sample maximum alone satisfies it. That is also why
    `TVaR >= VaR` holds: the mean of a set whose smallest member is at least the
    threshold cannot fall below it.
    """
    return float(annual_losses[annual_losses >= threshold].mean())
