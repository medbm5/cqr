"""Annualized attack frequency, expressed in episodes rather than alerts.

An alert is not an attack. One intrusion produces a burst of detections, so
counting alerts would measure the estate's detection verbosity rather than how
often it is attacked. This package filters telemetry to attack-grade events,
clusters them into episodes per asset, and scales the count to a
yearly rate using the observed window - `365 / observed_days`, never a hardcoded
horizon.

Typical use::

    from risk_engine.frequency import estimate_frequency

    estimate = estimate_frequency(
        result.events, result.report.window,
        assets=assets, normalization=result.report,
    )
    print(estimate.lambda_total)
    for line in estimate.to_explanation():
        print(line)
"""

from .attack_types import (
    TECHNIQUE_TO_ATTACK_TYPE,
    UNOBSERVABLE_ATTACK_TYPES,
    AttackType,
    attack_type_for,
)
from .episodes import (
    DAYS_PER_YEAR,
    DEFAULT_SESSION_GAP_HOURS,
    DEFAULT_SEVERITY_THRESHOLD,
    Episode,
    FrequencyParams,
    is_attack_grade,
    sessionize,
)
from .model import AssetFrequency, FrequencyEstimate, estimate_frequency

__all__ = [
    "DAYS_PER_YEAR",
    "DEFAULT_SESSION_GAP_HOURS",
    "DEFAULT_SEVERITY_THRESHOLD",
    "TECHNIQUE_TO_ATTACK_TYPE",
    "UNOBSERVABLE_ATTACK_TYPES",
    "AssetFrequency",
    "AttackType",
    "Episode",
    "FrequencyEstimate",
    "FrequencyParams",
    "attack_type_for",
    "estimate_frequency",
    "is_attack_grade",
    "sessionize",
]
