"""Severity scale translation between the two feeds.

The SIEM grades severity in four text classes; the EDR emits a number. This
module holds the single definition of how the two relate, so that no other part
of the engine has to know either vendor's vocabulary.
"""

from __future__ import annotations

from .models import SeverityClass

#: SIEM severity labels, mapped to the shared class vocabulary.
SIEM_SEVERITY_LABELS: dict[str, SeverityClass] = {
    "Low": SeverityClass.LOW,
    "Medium": SeverityClass.MEDIUM,
    "High": SeverityClass.HIGH,
    "Critical": SeverityClass.CRITICAL,
}

#: EDR `risk` cut points separating the four severity classes.
#:
#: Derived in `notebooks/01_eda.ipynb` section 4, not assumed. The 12,887 events
#: that both feeds reported *and* the SIEM graded form a labelled set: each one
#: carries a SIEM class and an EDR score for the same detection. A grid search
#: over every ordered triple of thresholds picks the one that reproduces the SIEM
#: label most often. The winner is (50, 70, 94), at 87.1% exact agreement and
#: 100.0% agreement within one class - the two tools never disagree by more than
#: a single grade.
#:
#: The choice is not delicate: rounding to (50, 70, 90) costs 0.4 points. The
#: alternative of matching the SIEM's marginal class shares gives (58, 76, 98)
#: and only 78.8% agreement, and was rejected - classifying each event correctly
#: matters more than reproducing totals.
EDR_CUT_POINTS: tuple[int, int, int] = (50, 70, 94)

#: Highest genuine EDR score. The field is documented as a 0-999 scale, but the
#: data does not use it that way: 19,344 of 19,350 rows fall in 0-100 and the
#: 99th percentile is 100 (`notebooks/01_eda.ipynb` section 4).
EDR_MAX_RISK = 100

#: Out-of-band value the EDR uses in place of a score, on six rows. It is a
#: sentinel, not a severity six times worse than the worst real detection, and
#: is read as "unknown" rather than ranked above every genuine event.
EDR_SENTINEL_RISK = 999


def severity_from_siem_label(label: str) -> SeverityClass:
    """Translate a SIEM severity label into the shared vocabulary.

    Args:
        label: One of `Low`, `Medium`, `High`, `Critical`.

    Returns:
        The matching severity class.

    Raises:
        ValueError: If the label is not one of the four known classes. Unknown
            labels are an error rather than a silent downgrade, because a
            vocabulary change upstream must not pass unnoticed.
    """
    try:
        return SIEM_SEVERITY_LABELS[label]
    except KeyError:
        raise ValueError(
            f"unknown SIEM severity label {label!r}; expected one of {sorted(SIEM_SEVERITY_LABELS)}"
        ) from None


def severity_from_edr_risk(risk: int) -> SeverityClass | None:
    """Translate an EDR risk score into the shared vocabulary.

    Applies `EDR_CUT_POINTS`: scores below 50 are Low, 50-69 Medium, 70-93 High,
    and 94 and above Critical.

    Args:
        risk: The raw `risk` value from the EDR feed.

    Returns:
        The matching severity class, or `None` for the `EDR_SENTINEL_RISK`
        placeholder, whose severity is genuinely unknown.

    Raises:
        ValueError: If the score is negative, or above `EDR_MAX_RISK` without
            being the known sentinel - an unrecognised out-of-range value is a
            data problem the caller must see, not one to silently clamp.
    """
    if risk == EDR_SENTINEL_RISK:
        return None
    if risk < 0 or risk > EDR_MAX_RISK:
        raise ValueError(
            f"EDR risk {risk} is outside the observed 0-{EDR_MAX_RISK} range and is "
            f"not the {EDR_SENTINEL_RISK} sentinel"
        )

    low, medium, high = EDR_CUT_POINTS
    if risk < low:
        return SeverityClass.LOW
    if risk < medium:
        return SeverityClass.MEDIUM
    if risk < high:
        return SeverityClass.HIGH
    return SeverityClass.CRITICAL
