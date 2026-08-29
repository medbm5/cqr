"""Monte Carlo aggregation of frequency and severity into an annual loss.

Frequency says how often each kind of attack lands; severity says what one costs.
Neither alone answers the question a board asks, which is what a *year* costs -
and that depends on how the two compound. A year with no ransomware and a year
with three are both ordinary; averaging the two stages analytically would hide
exactly the variance the exercise exists to quantify.

So each simulated year draws a Poisson count per attack type, draws that many
losses from that type's fitted distribution, and sums them. Ten thousand such
years are a distribution; a hundred thousand are a distribution with a readable
tail.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from risk_engine.attack_types import AttackType
from risk_engine.frequency import FrequencyEstimate
from risk_engine.severity import LognormalParams, SeverityModel

from .metrics import (
    ExceedanceCurve,
    LossHistogram,
    LossMetrics,
    exceedance_curve,
    log_spaced_probabilities,
    summarize,
)

Floats = npt.NDArray[np.float64]

#: Default number of simulated years.
#:
#: The tail is the point of the exercise, and a 1-in-10,000-year loss needs far
#: more than 10,000 years before its estimate stops moving between runs.
DEFAULT_N_YEARS = 100_000

#: Target number of individual loss draws held in memory at once.
#:
#: The simulation is vectorized across years, not looped over them, but a single
#: array of every incident in every year would be tens of gigabytes at the rates
#: this estate produces. Years are therefore processed in blocks sized so that
#: roughly this many draws are live at a time - a loop over a handful of blocks
#: rather than over a hundred thousand years.
DRAWS_PER_BLOCK = 20_000_000


@dataclass(frozen=True, slots=True)
class SimulationParams:
    """What the simulation was run with.

    Attributes:
        n_years: Simulated years.
        seed: Seed for every draw. The whole run is reproducible from it.
        draws_per_block: Memory budget, in individual loss draws. Affects speed
            and peak memory, never the result: the block boundaries are derived
            deterministically from the inputs, so the same seed and the same
            frequency and severity models always produce the same years.
    """

    n_years: int
    seed: int
    draws_per_block: int = DRAWS_PER_BLOCK


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """A simulated distribution of annual loss, and how it was produced.

    Attributes:
        metrics: Headline figures of the annual total.
        aep: Aggregate exceedance curve - the annual *total*.
        oep: Occurrence exceedance curve - the largest *single* loss in a year.
        annual_losses: Total loss per simulated year, ascending. Kept so a
            histogram - or a curve at a different resolution - can be drawn
            without re-running anything.
        annual_maxima: Largest single loss per simulated year, ascending. The
            OEP curve is read off this, at whatever resolution is asked for.
        expected_incidents_by_type: Mean incidents per year, per attack type -
            the Poisson rates the years were drawn from.
        expected_loss_by_type: Mean annual loss attributable to each attack type.
            These sum to the AAL and are what an "where does the risk come from"
            chart is made of.
        params: Seed, year count and memory budget.
        frequency: The frequency estimate the counts came from.
        severity: The severity model the losses came from.
    """

    metrics: LossMetrics
    aep: ExceedanceCurve
    oep: ExceedanceCurve
    annual_losses: Floats
    annual_maxima: Floats
    expected_incidents_by_type: Mapping[AttackType, float]
    expected_loss_by_type: Mapping[AttackType, float]
    params: SimulationParams
    frequency: FrequencyEstimate
    severity: SeverityModel

    def curve(self, kind: str, *, points: int) -> ExceedanceCurve:
        """Re-read an exceedance curve at a chosen resolution.

        The curves on this object are evaluated at a short list of round
        probabilities, which reads well in a table. A chart wants far more
        points, and re-deriving them from the stored per-year series costs a
        quantile call rather than another simulation.

        Args:
            kind: `"aep"` for the annual total, `"oep"` for the annual largest.
            points: How many points to evaluate, spaced on a log scale.

        Returns:
            The curve, limited to probabilities the run can actually resolve.

        Raises:
            ValueError: If `kind` is not aep or oep, or `points` is below 2.
        """
        series = {"aep": self.annual_losses, "oep": self.annual_maxima}.get(kind)
        if series is None:
            raise ValueError(f"kind must be 'aep' or 'oep', got {kind!r}")
        return exceedance_curve(
            series,
            kind=kind,
            probabilities=log_spaced_probabilities(points, finest=1.0 / series.size),
        )

    def histogram(self, *, bins: int = 40) -> LossHistogram:
        """Bin the simulated years for a distribution chart.

        Derived from the stored per-year series rather than returned by default,
        because the bin count is a presentation choice and the series is already
        here.

        Args:
            bins: Number of bins across the observed range.

        Returns:
            Bin edges in euros and the count of years in each.

        Raises:
            ValueError: If `bins` is below 1.
        """
        if bins < 1:
            raise ValueError(f"bins must be at least 1, got {bins}")
        counts, edges = np.histogram(self.annual_losses, bins=bins)
        return LossHistogram(
            bin_edges_eur=tuple(edges.tolist()),
            counts=tuple(int(count) for count in counts),
        )

    def to_explanation(self) -> list[str]:
        """Render the whole chain, from lambda and sigma through to the metrics."""
        lines: list[str] = []
        metrics = self.metrics

        lines.append(
            f"Simulated {self.params.n_years:,} independent year(s) from seed "
            f"{self.params.seed}, drawing a Poisson count per attack type and a "
            f"loss per incident."
        )

        lines.append(
            f"Frequency: {self.frequency.lambda_total:,.1f} attack(s) per year in total, "
            f"from {self.frequency.episodes:,} episode(s) over "
            f"{self.frequency.observed_days} observed day(s)."
        )
        lines.append("Severity: a lognormal per attack type, fitted on peer-weighted incidents.")
        lines.append("Per attack type, the inputs and what they contributed:")
        # Sorting the mapping's items rather than the enum itself: iterating a
        # StrEnum through sorted() widens the member type back to str.
        for attack_type, rate in sorted(
            self.frequency.lambda_by_attack_type.items(), key=lambda item: item[0].value
        ):
            if rate <= 0.0:
                continue
            fit = self.severity.fits[attack_type]
            contribution = self.expected_loss_by_type.get(attack_type, 0.0)
            share = contribution / metrics.aal if metrics.aal > 0 else 0.0
            lines.append(
                f"  {attack_type.value:18s} lambda={rate:>8,.1f}/yr  "
                f"mu={fit.params.mu:6.3f} sigma={fit.params.sigma:5.3f} "
                f"(mean EUR {fit.params.mean_eur:>12,.0f})  "
                f"-> EUR {contribution:>16,.0f}/yr, {share:5.1%} of AAL"
            )

        lines.append(
            f"Aggregated to an annual loss distribution over {self.params.n_years:,} year(s):"
        )
        lines.append(f"  AAL (mean)          EUR {metrics.aal:>18,.0f}")
        lines.append(f"  median year         EUR {metrics.median:>18,.0f}")
        lines.append(f"  VaR 95              EUR {metrics.var_95:>18,.0f}")
        lines.append(f"  TVaR 95             EUR {metrics.tvar_95:>18,.0f}")
        lines.append(f"  VaR 99              EUR {metrics.var_99:>18,.0f}")
        lines.append(f"  TVaR 99             EUR {metrics.tvar_99:>18,.0f}")
        lines.append(f"  worst simulated yr  EUR {metrics.maximum:>18,.0f}")
        lines.append(f"  years with no loss  {metrics.probability_of_no_loss:>18.2%}")

        if metrics.median > 0:
            lines.append(
                f"The AAL is {metrics.aal / metrics.median:.1f}x the median year: the "
                f"average is carried by rare severe years, not by typical ones."
            )
        lines.append(
            f"AEP is the annual total; OEP is the largest single loss in a year. At a "
            f"1-in-100-year probability the AEP curve reads EUR "
            f"{self._curve_at(self.aep, 0.01):,.0f} and the OEP curve EUR "
            f"{self._curve_at(self.oep, 0.01):,.0f}."
        )

        numbered: list[str] = []
        step = 0
        for line in lines:
            if line.startswith("  "):
                numbered.append(line)
            else:
                step += 1
                numbered.append(f"{step}. {line}")
        return numbered

    @staticmethod
    def _curve_at(curve: ExceedanceCurve, probability: float) -> float:
        """Read one point off a curve, or 0.0 when the run cannot resolve it."""
        for candidate, loss in zip(curve.exceedance_probability, curve.loss_eur, strict=True):
            if candidate == probability:
                return loss
        return 0.0


def simulate(
    frequency: FrequencyEstimate,
    severity: SeverityModel,
    *,
    n_years: int = DEFAULT_N_YEARS,
    seed: int = 42,
    draws_per_block: int = DRAWS_PER_BLOCK,
) -> SimulationResult:
    """Compound frequency and severity into a distribution of annual loss.

    For each attack type, each simulated year draws `Poisson(lambda_type)`
    incidents and one loss per incident from that type's fitted lognormal. The
    year's loss is the sum across every incident of every type.

    The work is vectorized: one Poisson draw for a whole block of years, one
    lognormal draw for every incident in that block, and one `bincount` to fold
    incidents back into their years. There is no per-year Python loop - only a
    loop over blocks, whose size is set by the memory budget.

    Args:
        frequency: Annualized rates per attack type.
        severity: Fitted loss distributions per attack type.
        n_years: Years to simulate. More years resolve a finer tail.
        seed: Seed for every draw in the run.
        draws_per_block: Approximate number of loss draws to hold at once.

    Returns:
        The simulated distribution, its metrics and both exceedance curves.

    Raises:
        ValueError: If `n_years` is not positive, or `draws_per_block` is not
            positive.
    """
    if n_years <= 0:
        raise ValueError(f"n_years must be positive, got {n_years}")
    if draws_per_block <= 0:
        raise ValueError(f"draws_per_block must be positive, got {draws_per_block}")

    rates = {
        attack_type: rate
        for attack_type, rate in frequency.lambda_by_attack_type.items()
        if rate > 0.0
    }
    params_by_type: dict[AttackType, LognormalParams] = {
        attack_type: severity.fits[attack_type].params for attack_type in rates
    }

    annual_losses = np.zeros(n_years, dtype=np.float64)
    annual_maxima = np.zeros(n_years, dtype=np.float64)
    loss_by_type: dict[AttackType, float] = dict.fromkeys(rates, 0.0)
    incidents_by_type: dict[AttackType, float] = dict.fromkeys(rates, 0.0)

    rng = np.random.default_rng(seed)
    for start, stop in _blocks(n_years, sum(rates.values()), draws_per_block):
        block = stop - start
        for attack_type, rate in rates.items():
            counts = rng.poisson(lam=rate, size=block)
            total = int(counts.sum())
            incidents_by_type[attack_type] += float(total)
            if total == 0:
                continue

            distribution = params_by_type[attack_type]
            losses = rng.lognormal(mean=distribution.mu, sigma=distribution.sigma, size=total)

            years = np.repeat(np.arange(block), counts)
            totals = np.bincount(years, weights=losses, minlength=block)
            annual_losses[start:stop] += totals
            loss_by_type[attack_type] += float(losses.sum())

            annual_maxima[start:stop] = np.maximum(
                annual_maxima[start:stop], _segment_maxima(losses, counts, block)
            )

    return SimulationResult(
        metrics=summarize(annual_losses),
        aep=exceedance_curve(annual_losses, kind="aep"),
        oep=exceedance_curve(annual_maxima, kind="oep"),
        annual_losses=np.sort(annual_losses),
        annual_maxima=np.sort(annual_maxima),
        expected_incidents_by_type={
            attack_type: total / n_years for attack_type, total in incidents_by_type.items()
        },
        expected_loss_by_type={
            attack_type: total / n_years for attack_type, total in loss_by_type.items()
        },
        params=SimulationParams(n_years=n_years, seed=seed, draws_per_block=draws_per_block),
        frequency=frequency,
        severity=severity,
    )


def _blocks(n_years: int, expected_per_year: float, draws_per_block: int) -> list[tuple[int, int]]:
    """Split the years into blocks small enough to hold in memory.

    The split depends only on the arguments, never on the machine, so a run is
    reproducible across environments: the same seed sees the same sequence of
    draws regardless of how much memory happens to be free.
    """
    if expected_per_year <= 0.0:
        return [(0, n_years)]

    years_per_block = max(1, int(draws_per_block / expected_per_year))
    return [
        (start, min(start + years_per_block, n_years))
        for start in range(0, n_years, years_per_block)
    ]


def _segment_maxima(losses: Floats, counts: npt.NDArray[np.int64], block: int) -> Floats:
    """Largest loss within each year of a block.

    `losses` is ordered by year, so each year is a contiguous run whose length is
    given by `counts`. Empty years are excluded from the reduction and left at
    zero: `np.maximum.reduceat` would otherwise read past the end of an empty
    segment and report a neighbouring year's loss.

    The caller only reaches here when the block holds at least one incident, so
    `non_empty` always selects something.
    """
    maxima = np.zeros(block, dtype=np.float64)
    non_empty = counts > 0
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    maxima[non_empty] = np.maximum.reduceat(losses, starts[non_empty])
    return maxima
