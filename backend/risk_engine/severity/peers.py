"""Soft peer weighting.

Severity should be calibrated on organisations comparable to the target - an ETI
in Retail, 1,200 employees, maturity 55/100. Hard filtering to exact matches
collapses immediately: it keeps 112 of 1,598 incidents, and once split across
eight attack types not one cell reaches 30 observations
(`notebooks/01_eda.ipynb` section 8).

The trade-off has no good discrete answer, which is the argument for not making
it discrete. Every incident carries a *degree* of similarity to the target; a
hard filter throws that away by rounding it to 0 or 1. Here each incident keeps
its degree as a weight, all of them contribute, and the closest dominate.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from .cleaning import Incident


@dataclass(frozen=True, slots=True)
class PeerWeightParams:
    """The target profile and how sharply similarity to it is rewarded.

    Every value is a parameter, and every default describes the case study's
    target company. Nothing here is inferred from the incident base: these are
    facts about the company being assessed.

    Attributes:
        target_sector: Sector of the target company.
        sector_match_weight: Weight for an incident in the target's sector.
        sector_other_weight: Weight for an incident in any other sector. Not
            zero - a ransomware loss in Industrie still carries information about
            ransomware - but clearly discounted.
        target_size: Size band of the target company.
        size_match_weight: Weight for an incident at a company of that size.
        size_other_weight: Weight for any other size band.
        target_maturity: Security maturity of the target, 0-100.
        maturity_bandwidth: Standard deviation of the Gaussian kernel applied to
            the maturity distance. Maturity in the base has a standard deviation
            of about 12, so a bandwidth of 15 keeps most of the base
            contributing while still favouring organisations defended about as
            well as the target. Smaller values sharpen the peer group toward the
            target and shrink the effective sample.
    """

    target_sector: str = "Retail"
    sector_match_weight: float = 1.0
    sector_other_weight: float = 0.4

    target_size: str = "ETI"
    size_match_weight: float = 1.0
    size_other_weight: float = 0.6

    target_maturity: float = 55.0
    maturity_bandwidth: float = 15.0

    def __post_init__(self) -> None:
        """Reject parameters that would make weights meaningless."""
        if self.maturity_bandwidth <= 0:
            raise ValueError(f"maturity_bandwidth must be positive, got {self.maturity_bandwidth}")
        negatives = {
            "sector_match_weight": self.sector_match_weight,
            "sector_other_weight": self.sector_other_weight,
            "size_match_weight": self.size_match_weight,
            "size_other_weight": self.size_other_weight,
        }
        for name, value in negatives.items():
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")


def sector_weight(sector: str, params: PeerWeightParams) -> float:
    """Similarity of an incident's sector to the target's."""
    return (
        params.sector_match_weight if sector == params.target_sector else params.sector_other_weight
    )


def size_weight(company_size: str, params: PeerWeightParams) -> float:
    """Similarity of an incident's size band to the target's."""
    return (
        params.size_match_weight if company_size == params.target_size else params.size_other_weight
    )


def maturity_weight(maturity: float, params: PeerWeightParams) -> float:
    """Similarity of an incident's security maturity to the target's.

    A Gaussian kernel on the absolute distance, `exp(-d^2 / 2h^2)`. Continuous
    rather than banded, because maturity is continuous: an organisation at 54 and
    one at 56 are equally good comparators for a target at 55, and a band edge
    between them would be an artefact of the bucketing, not of the data.

    Args:
        maturity: The incident organisation's maturity score.
        params: Target profile and bandwidth.

    Returns:
        A weight in (0, 1], reaching 1 at an exact match.
    """
    distance = abs(maturity - params.target_maturity)
    return math.exp(-(distance**2) / (2.0 * params.maturity_bandwidth**2))


def peer_weight(incident: Incident, params: PeerWeightParams) -> float:
    """Combined similarity of one incident to the target company.

    The three components multiply rather than add: an incident has to be
    plausible on *every* axis to weigh heavily, and being an exact sector match
    does not excuse being a very different size. A product also keeps the weight
    bounded by its weakest component, which is the conservative reading.

    Args:
        incident: The incident to weigh.
        params: Target profile and kernel settings.

    Returns:
        A non-negative weight, at most the product of the three match weights.
    """
    return (
        sector_weight(incident.sector, params)
        * size_weight(incident.company_size, params)
        * maturity_weight(incident.security_maturity_score, params)
    )


def peer_weights(
    incidents: Sequence[Incident], params: PeerWeightParams
) -> npt.NDArray[np.float64]:
    """Weight every incident against the target profile.

    Args:
        incidents: The incidents to weigh.
        params: Target profile and kernel settings.

    Returns:
        Weights aligned with `incidents`.
    """
    return np.array([peer_weight(incident, params) for incident in incidents], dtype=np.float64)


def effective_sample_size(weights: npt.NDArray[np.float64]) -> float:
    """Kish effective sample size, `(sum w)^2 / sum w^2`.

    A raw row count overstates how much a soft-weighted sample actually knows:
    1,598 incidents weighted mostly at 0.1 carry the information of far fewer.
    The Kish figure answers "how many equally-weighted observations would be
    worth as much as this?", and it is the number every fit is judged on. It
    equals the row count when all weights are equal, and falls toward 1 as the
    weight concentrates on a single incident.

    Args:
        weights: Non-negative weights.

    Returns:
        The effective sample size, or 0.0 when every weight is zero.
    """
    total = float(weights.sum())
    if total <= 0.0:
        return 0.0
    return total**2 / float((weights**2).sum())
