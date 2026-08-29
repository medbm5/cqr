"""Weighted lognormal fitting, and the diagnostics that challenge it.

The loss base is heavy-tailed: the mean is 15.6x the median, raw skewness is 7.4,
and the worst 1% of incidents carry 24% of all euros. Taking logs removes almost
all of that - skewness falls to 0.80 - which is why the fit is done on the log
scale (`notebooks/01_eda.ipynb` section 7).

The notebook also showed that a *single pooled* lognormal is rejected by KS
(D=0.107, p~2e-16), because the pool mixes five well-separated severity strata.
Fitting per attack type under peer weighting is the response, but it is not a
proof, so every fit here ships with the evidence against it: a weighted KS
statistic, QQ points, and a Pareto tail fitted to the same data as a rival
candidate. A fit whose tail a Pareto describes better is a fit to distrust.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy.special import ndtr, ndtri

Floats = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class LognormalParams:
    """A lognormal loss distribution, parameterized on the log scale.

    Attributes:
        mu: Mean of `ln(loss)`.
        sigma: Standard deviation of `ln(loss)`.
    """

    mu: float
    sigma: float

    @property
    def median_eur(self) -> float:
        """Median loss, `exp(mu)`. The loss a typical incident costs."""
        return math.exp(self.mu)

    @property
    def mean_eur(self) -> float:
        """Mean loss, `exp(mu + sigma^2 / 2)`.

        Always above the median, and far above it when sigma is large. This is
        the figure that drives the annualized expected loss, which is why the
        gap between the two is reported rather than left for the reader to
        notice.
        """
        return math.exp(self.mu + self.sigma**2 / 2.0)

    def quantile_eur(self, probability: float) -> float:
        """Loss at a given cumulative probability."""
        return math.exp(self.mu + self.sigma * _normal_ppf(probability))

    def cdf(self, loss: Floats) -> Floats:
        """Probability of a loss at or below each value."""
        with np.errstate(divide="ignore"):
            z = (np.log(loss) - self.mu) / self.sigma
        return _normal_cdf(z)


@dataclass(frozen=True, slots=True)
class ParetoTail:
    """A Pareto candidate for the upper tail, fitted as a rival to the lognormal.

    Attributes:
        threshold_eur: Loss above which the tail is modelled.
        alpha: Tail index from the weighted Hill estimator. Lower means heavier;
            below 2 the theoretical variance is infinite, below 1 the mean is.
        exceedances: Incidents above the threshold.
        ks_lognormal: Weighted KS of the lognormal on the tail alone.
        ks_pareto: Weighted KS of the Pareto on the same tail.

    """

    threshold_eur: float
    alpha: float
    exceedances: int
    ks_lognormal: float
    ks_pareto: float

    @property
    def pareto_fits_tail_better(self) -> bool:
        """Whether the Pareto describes the tail more closely than the lognormal.

        When true, the lognormal is understating the extreme losses that VaR and
        TVaR are made of, and the fit should be treated as a lower bound rather
        than as an estimate.
        """
        return self.ks_pareto < self.ks_lognormal


@dataclass(frozen=True, slots=True)
class FitDiagnostics:
    """Evidence for and against one fitted distribution.

    Attributes:
        observations: Incidents with a usable loss that fed the fit.
        effective_n: Kish effective sample size of the weights.
        weighted_ks: Sup-distance between the weighted empirical CDF and the
            fitted one. There is no p-value: the usual KS tables assume equal
            weights and known parameters, and neither holds here, so the
            statistic is reported as a comparable magnitude rather than dressed
            up as a test.
        qq_theoretical: Fitted quantiles of `ln(loss)`, for a QQ plot.
        qq_empirical: Observed quantiles of `ln(loss)`, aligned with the above.
        tail: The Pareto rival fitted to the upper tail, when enough
            observations exist above the threshold.
    """

    observations: int
    effective_n: float
    weighted_ks: float
    qq_theoretical: tuple[float, ...]
    qq_empirical: tuple[float, ...]
    tail: ParetoTail | None


def fit_lognormal(losses: Floats, weights: Floats) -> LognormalParams:
    """Fit a lognormal by weighted maximum likelihood on the log scale.

    For a lognormal the MLE has a closed form: `mu` is the weighted mean of
    `ln(loss)` and `sigma` its weighted standard deviation. No correction for
    bias is applied - the maximum-likelihood `sigma` is what the simulation
    stage needs to reproduce the fitted distribution, and with effective sample
    sizes in the hundreds the difference is far below the uncertainty in the
    inputs.

    Args:
        losses: Strictly positive losses in euros.
        weights: Non-negative weights aligned with `losses`.

    Returns:
        The fitted parameters.

    Raises:
        ValueError: If the inputs disagree in length, if any loss is not
            positive, or if the weights sum to zero - none of which can produce a
            distribution.
    """
    if losses.shape != weights.shape:
        raise ValueError(f"losses {losses.shape} and weights {weights.shape} must align")
    if losses.size == 0:
        raise ValueError("cannot fit a distribution to zero observations")
    if not bool(np.all(losses > 0.0)):
        raise ValueError("losses must be strictly positive to fit on the log scale")

    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("weights must sum to a positive value")

    log_losses = np.log(losses)
    mu = float(np.sum(weights * log_losses) / total)
    variance = float(np.sum(weights * (log_losses - mu) ** 2) / total)
    return LognormalParams(mu=mu, sigma=math.sqrt(variance))


def weighted_ks(losses: Floats, weights: Floats, params: LognormalParams) -> float:
    """Weighted Kolmogorov-Smirnov distance between data and fit.

    The empirical CDF is built from normalized weights rather than from counts,
    so a heavily discounted incident moves it less than a close peer. Both sides
    of each step are compared, as in the unweighted statistic.

    Args:
        losses: Positive losses.
        weights: Non-negative weights aligned with `losses`.
        params: The fitted distribution.

    Returns:
        The supremum distance, in [0, 1]. Zero means the fit reproduces the
        weighted sample exactly.
    """
    order = np.argsort(losses)
    ordered_losses = losses[order]
    ordered_weights = weights[order]

    total = float(ordered_weights.sum())
    if total <= 0.0:
        return 0.0

    upper = np.cumsum(ordered_weights) / total
    lower = upper - ordered_weights / total
    fitted = params.cdf(ordered_losses)
    return float(np.max(np.maximum(np.abs(upper - fitted), np.abs(lower - fitted))))


def qq_points(
    losses: Floats, weights: Floats, params: LognormalParams, *, points: int = 50
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Quantile pairs for a QQ plot of `ln(loss)`.

    Args:
        losses: Positive losses.
        weights: Non-negative weights aligned with `losses`.
        params: The fitted distribution.
        points: How many evenly spaced probabilities to evaluate.

    Returns:
        `(theoretical, empirical)` quantiles of `ln(loss)`, both ascending. A fit
        that describes the data traces the identity line; a heavy tail the model
        misses bends the upper end above it.
    """
    probabilities = (np.arange(points) + 0.5) / points
    theoretical = params.mu + params.sigma * np.array([_normal_ppf(p) for p in probabilities])
    empirical = np.log(np.array([weighted_quantile(losses, weights, p) for p in probabilities]))
    return tuple(theoretical.tolist()), tuple(empirical.tolist())


def weighted_quantile(losses: Floats, weights: Floats, probability: float) -> float:
    """Quantile of a weighted sample.

    Args:
        losses: Values to take the quantile of.
        weights: Non-negative weights aligned with `losses`.
        probability: Cumulative probability in [0, 1].

    Returns:
        The smallest value whose cumulative weight reaches `probability`.
    """
    order = np.argsort(losses)
    ordered_losses = losses[order]
    ordered_weights = weights[order]
    total = float(ordered_weights.sum())
    if total <= 0.0:
        return float(ordered_losses[0])

    cumulative = np.cumsum(ordered_weights) / total
    index = int(np.searchsorted(cumulative, probability, side="left"))
    return float(ordered_losses[min(index, ordered_losses.size - 1)])


def fit_pareto_tail(
    losses: Floats,
    weights: Floats,
    params: LognormalParams,
    *,
    tail_fraction: float = 0.10,
    min_exceedances: int = 15,
) -> ParetoTail | None:
    """Fit a Pareto to the upper tail and score it against the lognormal there.

    Why bother: AAL is driven by the body of the distribution, but VaR and TVaR
    are made almost entirely of the tail. A lognormal that fits the body well can
    still understate the extremes, and the only way to know is to fit something
    heavier to the same data and compare. `alpha` comes from the weighted Hill
    estimator, which is the maximum-likelihood tail index for exceedances over a
    threshold.

    Args:
        losses: Positive losses.
        weights: Non-negative weights aligned with `losses`.
        params: The fitted lognormal, scored on the tail for comparison.
        tail_fraction: Upper share of the weighted distribution to treat as tail.
        min_exceedances: Below this many exceedances the tail index is too noisy
            to mean anything, and `None` is returned instead.

    Returns:
        The tail comparison, or `None` when the tail is too thin to fit.
    """
    threshold = weighted_quantile(losses, weights, 1.0 - tail_fraction)
    above = losses > threshold
    if int(above.sum()) < min_exceedances:
        return None

    tail_losses = losses[above]
    tail_weights = weights[above]
    total = float(tail_weights.sum())
    if total <= 0.0:
        return None

    # Weighted Hill estimator: alpha = sum(w) / sum(w * ln(x / u)). The
    # denominator is strictly positive whenever the weights are: exceedances are
    # selected with a strict inequality, so every ln(x / u) term is above zero.
    log_excess = float(np.sum(tail_weights * np.log(tail_losses / threshold)))
    alpha = total / log_excess

    # Both candidates are scored as conditional distributions above the
    # threshold, so the comparison is like for like.
    survival_at_threshold = 1.0 - float(params.cdf(np.array([threshold]))[0])
    if survival_at_threshold <= 0.0:
        return None

    order = np.argsort(tail_losses)
    ordered = tail_losses[order]
    ordered_weights = tail_weights[order]
    upper = np.cumsum(ordered_weights) / total
    lower = upper - ordered_weights / total

    lognormal_conditional = (params.cdf(ordered) - (1.0 - survival_at_threshold)) / (
        survival_at_threshold
    )
    pareto_conditional = 1.0 - (threshold / ordered) ** alpha

    return ParetoTail(
        threshold_eur=threshold,
        alpha=alpha,
        exceedances=int(above.sum()),
        ks_lognormal=_sup_distance(upper, lower, lognormal_conditional),
        ks_pareto=_sup_distance(upper, lower, pareto_conditional),
    )


def diagnose(
    losses: Floats, weights: Floats, params: LognormalParams, effective_n: float
) -> FitDiagnostics:
    """Assemble every diagnostic for one fitted distribution."""
    theoretical, empirical = qq_points(losses, weights, params)
    return FitDiagnostics(
        observations=int(losses.size),
        effective_n=effective_n,
        weighted_ks=weighted_ks(losses, weights, params),
        qq_theoretical=theoretical,
        qq_empirical=empirical,
        tail=fit_pareto_tail(losses, weights, params),
    )


def _sup_distance(upper: Floats, lower: Floats, fitted: Floats) -> float:
    """Supremum distance between a stepped empirical CDF and a fitted one."""
    return float(np.max(np.maximum(np.abs(upper - fitted), np.abs(lower - fitted))))


def _normal_cdf(z: Floats) -> Floats:
    """Standard normal CDF."""
    return np.asarray(ndtr(z), dtype=np.float64)


def _normal_ppf(probability: float) -> float:
    """Standard normal quantile function."""
    return float(ndtri(probability))
