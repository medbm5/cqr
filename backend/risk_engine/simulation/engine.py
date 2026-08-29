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
    LossCap,
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
#:
#: A block costs **two** arrays of this length: the losses (float64) and the
#: year index each belongs to (int64). At 2,000,000 that is about 31 MB, which
#: fits comfortably inside a 512 MB container alongside the loaded dataset and
#: the fitted model. It was 20,000,000 - roughly 305 MB per block - which ran
#: fine on a workstation and OOM-killed the worker on a free-tier instance
#: within seconds of the first request.
#:
#: Raising it trades memory for a little speed. Note that changing it changes
#: the *sequence* of random draws, so two runs with the same seed but different
#: block sizes agree statistically rather than exactly.
DRAWS_PER_BLOCK = 2_000_000

#: Quantile of observed peer losses used as the default per-incident ceiling.
#:
#: The severity model fits a lognormal, which has no upper bound: at the sigmas
#: this data produces - 1.99 pooled, 2.41 on data breach, 2.58 on supply chain -
#: it will eventually draw a single incident costing more than the company is
#: worth, and a 100,000-year run is enough draws. On the case data the uncapped
#: worst simulated year reached EUR 3.8 billion for a company of 1,200 people.
#: The distribution says such a loss is possible; physical reality says it is
#: not, because a 1,200-employee ETI cannot lose more than it has. The tail
#: beyond the observed maximum is an artefact of the functional form, not
#: evidence.
#:
#: 0.999 of the cleaned incident base rather than its maximum: the maximum is a
#: single observation and moves with the next row added, while the 99.9th
#: percentile is a statement about the population that one outlier cannot swing.
DEFAULT_LOSS_CAP_QUANTILE = 0.999

#: Lowest bin edge for a log-scaled histogram, in euros.
#:
#: A log axis cannot start at zero and a year costing eleven euros is not a
#: distinct fact from one costing nine. Everything below folds into the first
#: bin, which is counted separately so the bar can say so.
HISTOGRAM_FLOOR_EUR = 1_000.0


@dataclass(frozen=True, slots=True)
class SimulationParams:
    """What the simulation was run with.

    Attributes:
        n_years: Simulated years.
        seed: Seed for every draw. The whole run is reproducible from it.
        loss_cap_eur: Per-incident ceiling every drawn loss was clipped to.
        draws_per_block: Memory budget, in individual loss draws. A block holds
            two arrays of this length, so peak memory is about 16 bytes times
            this number. Reproducibility is exact for a *fixed* value - the same
            seed and inputs always give the same years - but changing it changes
            the order draws are taken in, so results across different block
            sizes agree statistically rather than to the last euro.
    """

    n_years: int
    seed: int
    loss_cap_eur: float
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
        cap: What the per-incident plausibility cap did to the run.
        params: Seed, year count, cap and memory budget.
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
    cap: LossCap
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

    def histogram(
        self,
        *,
        bins: int = 40,
        scale: str = "log",
        floor_eur: float = HISTOGRAM_FLOOR_EUR,
    ) -> LossHistogram:
        """Bin the simulated years for a distribution chart.

        Derived from the stored per-year series rather than returned by default,
        because the bin count is a presentation choice and the series is already
        here.

        Two presentation decisions are made here rather than in the client,
        because both are needed to make the chart readable at all and a client
        that got them wrong would misrepresent the model:

        **Zero-loss years are separated.** Roughly three years in four cost
        nothing, so binning them with the rest gives one bar holding 73% of the
        mass and thirty-nine bars indistinguishable from the axis.

        **Bins are log-spaced by default.** Annual losses span from a few
        hundred euros to tens of millions. Linear bins of that range put every
        loss-year in the first two, which is the same failure again.

        Args:
            bins: Number of bins across the loss-years' range.
            scale: `"log"` for log-spaced edges, `"linear"` for equal ones.
            floor_eur: Lowest bin edge on a log scale. Loss-years below it are
                folded into the first bin and counted in `below_floor_years`.

        Returns:
            The bins, the zero-year count, and how many loss-years fell below
            the floor.

        Raises:
            ValueError: If `bins` is below 1, `scale` is not log or linear, or
                `floor_eur` is not positive.
        """
        if bins < 1:
            raise ValueError(f"bins must be at least 1, got {bins}")
        if scale not in {"log", "linear"}:
            raise ValueError(f"scale must be 'log' or 'linear', got {scale!r}")
        if floor_eur <= 0.0:
            raise ValueError(f"floor_eur must be positive, got {floor_eur}")

        losses = self.annual_losses
        positive = losses[losses > 0.0]
        zero_years = int(losses.size - positive.size)

        if positive.size == 0:
            # Every year cost nothing. There is no distribution to bin, and
            # inventing edges over an empty range would only produce a chart of
            # noise - the zero-year count carries the whole finding.
            return LossHistogram(
                bin_edges_eur=(),
                counts=(),
                zero_years=zero_years,
                loss_years=0,
                below_floor_years=0,
                scale=scale,
            )

        top = float(positive.max())
        if scale == "linear":
            edges = np.linspace(float(positive.min()), top, bins + 1)
            below_floor = 0
        else:
            # Honour the requested floor unless it would invert the range - a
            # run whose worst year costs less than the floor has no bins to
            # draw. Clamping it whenever it merely sits high would silently
            # ignore a caller who asked for a floor on purpose.
            low = floor_eur if floor_eur < top else top / 10.0
            edges = np.logspace(np.log10(low), np.log10(top), bins + 1)
            below_floor = int(np.count_nonzero(positive < low))

        # Clip rather than drop: a year below the floor is still a loss-year,
        # and letting np.histogram discard it would leave the bars summing to
        # less than the loss-year count with nothing on screen saying so.
        counts, _ = np.histogram(np.clip(positive, edges[0], edges[-1]), bins=edges)
        return LossHistogram(
            bin_edges_eur=tuple(float(edge) for edge in edges),
            counts=tuple(int(count) for count in counts),
            zero_years=zero_years,
            loss_years=int(positive.size),
            below_floor_years=below_floor,
            scale=scale,
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

        calibration = self.frequency.calibration
        lines.append(
            f"Frequency: {self.frequency.lambda_detected:,.1f} DETECTED attack(s) per "
            f"year, from {self.frequency.episodes:,} episode(s) over "
            f"{self.frequency.observed_days} observed day(s)."
        )
        if calibration is not None:
            lines.append(
                f"  Calibrated to {calibration.lambda_incident:.4f} LOSS INCIDENT(s) per "
                f"year (p_materialize = {calibration.p_materialize:.2e}), anchored on "
                f"{calibration.base_rate.companies:,} peer organisation(s). The "
                f"simulation draws from this, not from the detection rate."
            )
        lines.append("Severity: a lognormal per attack type, fitted on peer-weighted incidents.")

        cap = self.cap
        source = (
            f"the {cap.quantile * 100:.1f}th percentile of the "
            f"{self.severity.incidents_fitted:,} cleaned peer loss(es)"
            if cap.quantile is not None
            else "a caller-supplied ceiling"
        )
        widest = max(
            (
                self.severity.fits[attack_type].params.sigma
                for attack_type in self.expected_loss_by_type
            ),
            default=self.severity.pooled.params.sigma,
        )
        lines.append(
            f"Capped every single incident loss at EUR {cap.cap_eur:,.0f} - {source}. An "
            f"unbounded lognormal at sigma {widest:.2f} will eventually draw one incident "
            f"costing more than the company is worth; that draw is the functional form "
            f"extrapolating past every observation it was fitted on, not evidence."
        )
        lines.append(
            f"  {cap.draws_capped:,} of {cap.draws_total:,} drawn incident(s) hit the "
            f"ceiling ({cap.share_capped:.3%}). AAL uncapped EUR {cap.aal_uncapped:,.0f} "
            f"-> capped EUR {metrics.aal:,.0f}, a reduction of "
            f"{cap.aal_reduction(metrics.aal):.1%}."
        )

        lines.append("Per attack type, the inputs and what they contributed:")
        # Sorting the mapping's items rather than the enum itself: iterating a
        # StrEnum through sorted() widens the member type back to str.
        for attack_type, rate in sorted(
            (self.frequency.lambda_incident_by_attack_type or {}).items(),
            key=lambda item: item[0].value,
        ):
            if rate <= 0.0:
                continue
            fit = self.severity.fits[attack_type]
            contribution = self.expected_loss_by_type.get(attack_type, 0.0)
            share = contribution / metrics.aal if metrics.aal > 0 else 0.0
            lines.append(
                f"  {attack_type.value:18s} lambda={rate:>9,.5f}/yr  "
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
    loss_cap_eur: float | None = None,
    draws_per_block: int = DRAWS_PER_BLOCK,
) -> SimulationResult:
    """Compound frequency and severity into a distribution of annual loss.

    For each attack type, each simulated year draws `Poisson(lambda_type)`
    incidents and one loss per incident from that type's fitted lognormal, capped
    at `loss_cap_eur`. The year's loss is the sum across every incident of every
    type.

    **Why the cap.** A lognormal has no upper bound. Fitted on this data it
    carries sigmas from 1.37 to 2.58, and a distribution that wide will, given
    enough draws, price a single incident above ten times the target company's
    plausible revenue - a 100,000-year run is enough draws, and on the case data
    the uncapped worst year reached EUR 3.8 billion. Those draws are not a
    forecast of a catastrophic breach; they are the functional form extrapolating
    past every observation it was fitted on. Real losses are bounded by what the
    organisation can actually lose: its cash, its receivables, its customers, its
    market value. Clipping each incident to the 99.9th percentile of what
    comparable organisations were actually observed to lose keeps the tail heavy
    - it remains two orders of magnitude above the median incident - while
    refusing to let an unbounded functional form invent the top of it.

    The cap binds per *incident*, not per year: a year with three capped
    incidents costs three times the cap, which is correct. Only the single
    implausible loss is disallowed, not the accumulation of plausible ones.

    The work is vectorized: one Poisson draw for a whole block of years, one
    lognormal draw for every incident in that block, and one `bincount` to fold
    incidents back into their years. There is no per-year Python loop - only a
    loop over blocks, whose size is set by the memory budget.

    Args:
        frequency: Annualized rates per attack type.
        severity: Fitted loss distributions per attack type.
        n_years: Years to simulate. More years resolve a finer tail.
        seed: Seed for every draw in the run.
        loss_cap_eur: Per-incident ceiling in euros. Defaults to the
            `DEFAULT_LOSS_CAP_QUANTILE` quantile of the cleaned peer losses the
            severity model was fitted on - roughly EUR 23M on the case data.
            Pass `math.inf` to run genuinely uncapped.
        draws_per_block: Approximate number of loss draws to hold at once.

    Returns:
        The simulated distribution, its metrics, both exceedance curves, and a
        `cap` record giving how many draws were clipped and what the average
        annual loss would have been without the cap.

    Raises:
        ValueError: If `n_years` is not positive, if `draws_per_block` is not
            positive, if `loss_cap_eur` is not positive, or if the frequency
            estimate has not been calibrated into incident rates.
    """
    if n_years <= 0:
        raise ValueError(f"n_years must be positive, got {n_years}")
    if draws_per_block <= 0:
        raise ValueError(f"draws_per_block must be positive, got {draws_per_block}")
    if loss_cap_eur is not None and loss_cap_eur <= 0.0:
        raise ValueError(f"loss_cap_eur must be positive, got {loss_cap_eur}")

    cap_quantile = None if loss_cap_eur is not None else DEFAULT_LOSS_CAP_QUANTILE
    cap = (
        loss_cap_eur
        if loss_cap_eur is not None
        else severity.loss_quantile(DEFAULT_LOSS_CAP_QUANTILE)
    )

    # The *incident* rate, never the detection rate. The severity model prices
    # incidents that produced a loss, so drawing Poisson counts from detected
    # episodes would price every alert as a breach - a category error worth
    # failing loudly on rather than silently computing.
    incident_rates = frequency.lambda_incident_by_attack_type
    if incident_rates is None and frequency.episodes == 0:
        # Nothing was detected, so nothing materialises. A legitimate zero, not
        # a missing calibration - the distinction matters because one is an
        # answer and the other is a bug.
        incident_rates = {}
    if incident_rates is None:
        raise ValueError(
            "frequency estimate is uncalibrated: it reports detected attacks, not "
            "loss-generating incidents. Pass the incident base to estimate_frequency() "
            "so the two can be reconciled before they are multiplied."
        )
    rates = {attack_type: rate for attack_type, rate in incident_rates.items() if rate > 0.0}
    params_by_type: dict[AttackType, LognormalParams] = {
        attack_type: severity.fits[attack_type].params for attack_type in rates
    }

    annual_losses = np.zeros(n_years, dtype=np.float64)
    annual_maxima = np.zeros(n_years, dtype=np.float64)
    loss_by_type: dict[AttackType, float] = dict.fromkeys(rates, 0.0)
    incidents_by_type: dict[AttackType, float] = dict.fromkeys(rates, 0.0)
    draws_capped = 0
    draws_total = 0
    uncapped_sum = 0.0

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

            # The uncapped total is accumulated as a scalar rather than a second
            # per-year array: the comparison the reader needs is of averages, and
            # a running sum costs nothing where another n_years array costs
            # memory the block budget exists to protect.
            draws_total += total
            uncapped_sum += float(losses.sum())
            draws_capped += int(np.count_nonzero(losses > cap))
            losses = np.minimum(losses, cap)

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
        cap=LossCap(
            cap_eur=cap,
            quantile=cap_quantile,
            draws_capped=draws_capped,
            draws_total=draws_total,
            aal_uncapped=uncapped_sum / n_years,
        ),
        params=SimulationParams(
            n_years=n_years,
            seed=seed,
            loss_cap_eur=cap,
            draws_per_block=draws_per_block,
        ),
        frequency=frequency,
        severity=severity,
    )


def _blocks(n_years: int, expected_per_year: float, draws_per_block: int) -> list[tuple[int, int]]:
    """Split the years into blocks small enough to hold in memory.

    The split depends only on the arguments, never on the machine, so a run is
    reproducible across environments: for a given `draws_per_block`, the same
    seed sees the same sequence of draws no matter how much memory is free.
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
