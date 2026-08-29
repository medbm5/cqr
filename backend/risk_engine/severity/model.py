"""The severity model: what one attack of each type costs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from risk_engine.attack_types import AttackType

from .cleaning import CleaningReport, Incident
from .fitting import FitDiagnostics, LognormalParams, diagnose, fit_lognormal
from .peers import PeerWeightParams, effective_sample_size, peer_weights

#: Effective sample size below which a per-attack-type fit is not trusted.
#:
#: Not derived from the data - a convention, and the conventional one. It is
#: binding here: hard-filtering the base to exact peers leaves zero of eight
#: attack types above it (`notebooks/01_eda.ipynb` section 8), which is the
#: argument for soft weighting in the first place.
DEFAULT_MIN_EFFECTIVE_N = 30.0


@dataclass(frozen=True, slots=True)
class SeverityFit:
    """One fitted loss distribution and how much it should be trusted.

    Attributes:
        attack_type: The type this fit prices.
        params: The fitted lognormal.
        diagnostics: Evidence for and against it. When `used_pooled` is set and
            the type had no incidents at all, these are the pooled diagnostics -
            so read `own_observations`, not `diagnostics.observations`, for how
            much data this type actually contributed.
        own_observations: Incidents of this type with a usable loss. Zero is
            possible, and is why this is tracked apart from the diagnostics.
        own_effective_n: Kish effective sample size of this type's own peers,
            the number the fallback threshold is compared against.
        used_pooled: True when the type's own peer sample was too thin and the
            pooled fit was substituted. The substitution is recorded rather than
            hidden, because a pooled fit prices a ransomware attack at the
            average cost of every attack type.
    """

    attack_type: AttackType
    params: LognormalParams
    diagnostics: FitDiagnostics
    own_observations: int
    own_effective_n: float
    used_pooled: bool


@dataclass(frozen=True, slots=True)
class SeverityModel:
    """Loss distributions per attack type, fitted on soft-weighted peers.

    Attributes:
        fits: One fit per attack type present in the incident base, plus every
            type the engine knows about.
        pooled: The fit over all peer-weighted incidents, used as the fallback.
        peer_params: The target profile the weights were built from.
        cleaning: What the cleaning pass did to the incident base.
        min_effective_n: The threshold that triggered any fallbacks.
        incidents_total: Incidents read.
        incidents_fitted: Incidents with a usable loss.
    """

    fits: Mapping[AttackType, SeverityFit]
    pooled: SeverityFit
    peer_params: PeerWeightParams
    cleaning: CleaningReport
    min_effective_n: float
    incidents_total: int
    incidents_fitted: int

    @property
    def params_by_type(self) -> Mapping[AttackType, LognormalParams]:
        """The fitted parameters, keyed by attack type."""
        return {attack_type: fit.params for attack_type, fit in self.fits.items()}

    @property
    def fit_diagnostics(self) -> Mapping[AttackType, FitDiagnostics]:
        """The diagnostics for each fit, keyed by attack type."""
        return {attack_type: fit.diagnostics for attack_type, fit in self.fits.items()}

    def sample(
        self, attack_type: AttackType, n: int, rng: np.random.Generator
    ) -> npt.NDArray[np.float64]:
        """Draw `n` losses for attacks of one type.

        Args:
            attack_type: The type to price. A type with no fit of its own draws
                from the pooled distribution.
            n: How many losses to draw. Zero is valid and returns an empty array,
                which is the common case in simulation - most attack types do not
                occur in most simulated years.
            rng: The generator to draw from. Passed in rather than created here,
                so a whole simulation run is reproducible from one seed.

        Returns:
            `n` losses in euros, all strictly positive.

        Raises:
            ValueError: If `n` is negative.
        """
        if n < 0:
            raise ValueError(f"cannot draw a negative number of losses: {n}")

        params = self.fits.get(attack_type, self.pooled).params
        return np.asarray(
            rng.lognormal(mean=params.mu, sigma=params.sigma, size=n), dtype=np.float64
        )

    def to_explanation(self) -> list[str]:
        """Render the model as a numbered, human-readable trace.

        Returns:
            The cleaning trace, the peer profile, then one block per attack type
            giving its sample size, effective sample size, fitted parameters and
            what they imply in euros.
        """
        lines = list(self.cleaning.to_explanation())
        step = len(lines)

        params = self.peer_params
        step += 1
        lines.append(
            f"{step}. Weighted every incident against the target profile: "
            f"{params.target_sector} sector, {params.target_size}, maturity "
            f"{params.target_maturity:g}/100."
        )
        lines.append(
            f"  weight = w_sector x w_size x exp(-d^2 / 2h^2), with "
            f"w_sector = {params.sector_match_weight:g} on a match else "
            f"{params.sector_other_weight:g}, w_size = {params.size_match_weight:g} "
            f"on a match else {params.size_other_weight:g}, and h = "
            f"{params.maturity_bandwidth:g} on the maturity distance d."
        )
        lines.append(
            f"  No incident is discarded: all {self.incidents_fitted:,} with a usable "
            f"loss contribute, the closest ones dominating."
        )

        step += 1
        lines.append(
            f"{step}. Fitted a lognormal per attack type by weighted maximum "
            f"likelihood on log-losses, falling back to the pooled fit below an "
            f"effective sample size of {self.min_effective_n:g}."
        )
        pooled = self.pooled
        lines.append(
            f"  pooled: n_eff {pooled.own_effective_n:,.1f} of "
            f"{pooled.own_observations:,} incident(s), mu="
            f"{pooled.params.mu:.4f} sigma={pooled.params.sigma:.4f} -> median "
            f"EUR {pooled.params.median_eur:,.0f}, mean EUR {pooled.params.mean_eur:,.0f}."
        )

        for attack_type, fit in sorted(self.fits.items(), key=lambda item: item[0].value):
            if not fit.used_pooled:
                note = ""
            elif fit.own_observations == 0:
                note = "  [no incidents of this type -> pooled]"
            else:
                note = f"  [n_eff < {self.min_effective_n:g} -> pooled]"
            lines.append(
                f"  {attack_type.value:18s} n={fit.own_observations:>4,} "
                f"n_eff={fit.own_effective_n:>7,.1f}  "
                f"mu={fit.params.mu:6.3f} sigma={fit.params.sigma:5.3f}  "
                f"median EUR {fit.params.median_eur:>10,.0f}  "
                f"mean EUR {fit.params.mean_eur:>12,.0f}{note}"
            )

        step += 1
        lines.append(f"{step}. Challenged every fit against the data it was fitted to.")
        for attack_type, fit in sorted(self.fits.items(), key=lambda item: item[0].value):
            diagnostics = fit.diagnostics
            tail = diagnostics.tail
            if tail is None:
                verdict = "tail too thin to test"
            elif tail.pareto_fits_tail_better:
                verdict = (
                    f"a Pareto tail (alpha={tail.alpha:.2f}) describes the top "
                    f"{tail.exceedances} loss(es) better - extremes likely understated"
                )
            else:
                verdict = f"lognormal beats a Pareto tail (alpha={tail.alpha:.2f})"
            lines.append(
                f"  {attack_type.value:18s} weighted KS={diagnostics.weighted_ks:.4f}; {verdict}."
            )

        step += 1
        lines.append(
            f"{step}. A mean far above the median is the tail, not an error: the "
            f"pooled fit prices the typical incident at EUR "
            f"{pooled.params.median_eur:,.0f} and the average one at EUR "
            f"{pooled.params.mean_eur:,.0f}, "
            f"{pooled.params.mean_eur / pooled.params.median_eur:.1f}x higher."
        )
        return lines


def fit_severity_model(
    incidents: Sequence[Incident],
    cleaning: CleaningReport,
    *,
    peer_params: PeerWeightParams | None = None,
    min_effective_n: float = DEFAULT_MIN_EFFECTIVE_N,
) -> SeverityModel:
    """Fit the severity model on soft-weighted comparable incidents.

    One lognormal is fitted per attack type on that type's incidents, weighted by
    similarity to the target company. Where a type's effective sample size falls
    below `min_effective_n`, the pooled fit is used instead and the substitution
    is recorded - a thin sample produces confident-looking parameters that mean
    nothing, and silently shipping them would be the worse failure.

    Args:
        incidents: Cleaned incidents from `load_incidents`.
        cleaning: The report from the same call, carried into the explanation.
        peer_params: Target profile and kernel settings. Defaults to the case
            study's company.
        min_effective_n: Kish effective sample size below which a per-type fit
            falls back to pooled.

    Returns:
        The fitted model.

    Raises:
        ValueError: If no incident carries a usable loss, leaving nothing to fit.
    """
    params = peer_params if peer_params is not None else PeerWeightParams()

    usable = [incident for incident in incidents if incident.loss_eur is not None]
    if not usable:
        raise ValueError("no incident carries a usable loss; nothing to fit")

    losses = np.array([incident.loss_eur for incident in usable], dtype=np.float64)
    weights = peer_weights(usable, params)

    pooled_params = fit_lognormal(losses, weights)
    pooled = SeverityFit(
        attack_type=AttackType.OTHER,
        params=pooled_params,
        diagnostics=diagnose(losses, weights, pooled_params, effective_sample_size(weights)),
        own_observations=int(losses.size),
        own_effective_n=effective_sample_size(weights),
        used_pooled=False,
    )

    fits: dict[AttackType, SeverityFit] = {}
    for attack_type in AttackType:
        selected = np.array(
            [incident.attack_type is attack_type for incident in usable], dtype=bool
        )
        type_losses = losses[selected]
        type_weights = weights[selected]
        type_effective_n = effective_sample_size(type_weights)

        if type_losses.size == 0 or type_effective_n < min_effective_n:
            # Too thin to speak for itself: price it at the pooled rate, and say so.
            fits[attack_type] = SeverityFit(
                attack_type=attack_type,
                params=pooled.params,
                diagnostics=(
                    pooled.diagnostics
                    if type_losses.size == 0
                    else diagnose(type_losses, type_weights, pooled.params, type_effective_n)
                ),
                own_observations=int(type_losses.size),
                own_effective_n=type_effective_n,
                used_pooled=True,
            )
            continue

        type_params = fit_lognormal(type_losses, type_weights)
        fits[attack_type] = SeverityFit(
            attack_type=attack_type,
            params=type_params,
            diagnostics=diagnose(type_losses, type_weights, type_params, type_effective_n),
            own_observations=int(type_losses.size),
            own_effective_n=type_effective_n,
            used_pooled=False,
        )

    return SeverityModel(
        fits=fits,
        pooled=pooled,
        peer_params=params,
        cleaning=cleaning,
        min_effective_n=min_effective_n,
        incidents_total=len(incidents),
        incidents_fitted=len(usable),
    )
