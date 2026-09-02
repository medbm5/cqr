"""Converting detected attacks into loss-generating incidents.

**These are different units, and conflating them is a category error.**

The telemetry counts what the sensors *saw*: episodes of attack-grade activity on
an asset. The severity model prices what an incident *cost*, fitted on a base
where every row is an incident that actually produced a loss. Multiplying one by
the other prices every detection as though it were a breach, which is how a
20-asset company arrives at an annual loss of twelve billion euros.

Almost every detected attack is stopped, or is noise, or is one step of a chain
that never completes. The conversion factor - what share of detected attacks
materialise into a loss - is `p_materialize`, and it is not knowable from the
telemetry alone, because the telemetry contains no outcomes. It is calibrated
instead against the external base: over ~4 years, 1,310 organisations recorded
1,600 incidents, which is about 0.31 loss events per organisation-year.

The peer weighting from the severity module is reused deliberately. Basing the
anchor on the raw mean would answer "how often does an average organisation get
hurt"; weighting it answers "how often does an organisation like *this* one get
hurt", which is the question being asked.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from risk_engine.severity.cleaning import Incident
from risk_engine.severity.peers import PeerWeightParams, peer_weight

#: Days in a year, matching `episodes.DAYS_PER_YEAR`.
DAYS_PER_YEAR = 365.0


@dataclass(frozen=True, slots=True)
class BaseRate:
    """How often an organisation like the target suffers a loss-generating incident.

    Attributes:
        incidents_per_company_year: The peer-weighted rate. The anchor.
        weighted_incidents: Sum of incident weights - the numerator.
        weighted_companies: Sum of company weights - the denominator, before
            multiplying by the observed span.
        companies: Distinct organisations in the base.
        incidents: Incidents in the base.
        observed_years: Span the base covers, computed from its own dates.
    """

    incidents_per_company_year: float
    weighted_incidents: float
    weighted_companies: float
    companies: int
    incidents: int
    observed_years: float


@dataclass(frozen=True, slots=True)
class Calibration:
    """The bridge from detected attacks to priced incidents.

    Attributes:
        lambda_detected: Attack episodes per year, from the telemetry.
        lambda_incident: Loss-generating incidents per year, after calibration.
            This is the rate the simulation draws from.
        p_materialize: The share of detected attacks that become losses.
            Deliberately a single scalar rather than a model: making it
            maturity-dependent would need an exposure denominator the incident
            base does not carry, so one visible number is the honest version.
        base_rate: The external anchor it was fitted against.
    """

    lambda_detected: float
    lambda_incident: float
    p_materialize: float
    base_rate: BaseRate


def peer_weighted_base_rate(incidents: Sequence[Incident], params: PeerWeightParams) -> BaseRate:
    """Incidents per organisation-year among organisations resembling the target.

    Both the numerator and the denominator are weighted by the same similarity
    kernel: incidents count in proportion to how much the affected organisation
    resembles the target, and organisation-years count the same way. Weighting
    only the numerator would inflate the rate by dividing peer incidents by every
    organisation in the base.

    Args:
        incidents: The cleaned external incident base.
        params: The same target profile the severity model weights against.

    Returns:
        The anchor rate and the quantities behind it.

    Raises:
        ValueError: If the base is empty, spans no time, or carries no weight -
            none of which can produce a rate.
    """
    if not incidents:
        raise ValueError("cannot derive a base rate from an empty incident base")

    dates = [incident.occurred_on for incident in incidents]
    observed_years = (max(dates) - min(dates)).days / 365.25
    if observed_years <= 0:
        raise ValueError("incident base spans no time; cannot derive an annual rate")

    # One record per organisation: the attributes are properties of the company,
    # not of the incident, so a company appearing three times is still one
    # company-year of exposure per year.
    per_company: dict[str, Incident] = {}
    for incident in incidents:
        per_company.setdefault(incident.company_id, incident)

    weighted_incidents = sum(peer_weight(incident, params) for incident in incidents)
    weighted_companies = sum(peer_weight(company, params) for company in per_company.values())
    if weighted_companies <= 0.0:
        raise ValueError("no organisation in the base carries any weight for this profile")

    return BaseRate(
        incidents_per_company_year=weighted_incidents / (weighted_companies * observed_years),
        weighted_incidents=weighted_incidents,
        weighted_companies=weighted_companies,
        companies=len(per_company),
        incidents=len(incidents),
        observed_years=observed_years,
    )


def calibrate(lambda_detected: float, base_rate: BaseRate) -> Calibration:
    """Fit the detected-to-incident conversion against the external anchor.

    `p_materialize` is whatever makes the two agree:

        lambda_incident = base_rate
        p_materialize   = base_rate / lambda_detected

    It is a fitted quantity, not an assumption - which is why it is reported
    rather than configured. A very small value is not a red flag in itself; it is
    the honest statement that this estate's sensors fire far more often than
    comparable organisations actually lose money. It *is* worth reading as a
    diagnostic: an implausibly small `p_materialize` says the detection stream is
    noisier than the peer group's, not that the company is safer.

    Args:
        lambda_detected: Annualized attack episodes from the telemetry.
        base_rate: The peer-weighted external anchor.

    Returns:
        Both rates and the factor between them.

    Raises:
        ValueError: If `lambda_detected` is not positive. With no detected
            attacks there is nothing to scale, and the incident rate would have
            to come from the base alone.
    """
    if lambda_detected <= 0.0:
        raise ValueError(
            f"cannot calibrate against {lambda_detected} detected attacks per year; "
            f"with no detections the incident rate is the base rate itself"
        )

    return Calibration(
        lambda_detected=lambda_detected,
        lambda_incident=base_rate.incidents_per_company_year,
        p_materialize=base_rate.incidents_per_company_year / lambda_detected,
        base_rate=base_rate,
    )
