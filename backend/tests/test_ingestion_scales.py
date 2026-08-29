"""Severity scale translation, including every cut-point boundary."""

import pytest

from risk_engine.ingestion import (
    EDR_CUT_POINTS,
    EDR_MAX_RISK,
    EDR_SENTINEL_RISK,
    SeverityClass,
    severity_from_edr_risk,
    severity_from_siem_label,
)


@pytest.mark.parametrize(
    ("label", "expected", "score"),
    [
        ("Low", SeverityClass.LOW, 0.25),
        ("Medium", SeverityClass.MEDIUM, 0.50),
        ("High", SeverityClass.HIGH, 0.75),
        ("Critical", SeverityClass.CRITICAL, 1.00),
    ],
)
def test_siem_labels_map_to_the_documented_scores(label, expected, score):
    assert severity_from_siem_label(label) is expected
    assert severity_from_siem_label(label).score == score


def test_unknown_siem_label_is_an_error_not_a_downgrade():
    with pytest.raises(ValueError, match="unknown SIEM severity label"):
        severity_from_siem_label("Informational")


@pytest.mark.parametrize(
    ("risk", "expected"),
    [
        # Boundaries either side of each cut point (50, 70, 94).
        (0, SeverityClass.LOW),
        (49, SeverityClass.LOW),
        (50, SeverityClass.MEDIUM),
        (69, SeverityClass.MEDIUM),
        (70, SeverityClass.HIGH),
        (93, SeverityClass.HIGH),
        (94, SeverityClass.CRITICAL),
        (100, SeverityClass.CRITICAL),
    ],
)
def test_edr_cut_points_are_inclusive_lower_exclusive_upper(risk, expected):
    assert severity_from_edr_risk(risk) is expected


def test_cut_points_match_the_values_derived_in_the_notebook():
    assert EDR_CUT_POINTS == (50, 70, 94)


def test_sentinel_risk_is_unknown_not_maximal():
    # The six 999 rows in the real feed are an out-of-band placeholder. Ranking
    # them as scores would put them above every genuine detection.
    assert severity_from_edr_risk(EDR_SENTINEL_RISK) is None


@pytest.mark.parametrize("risk", [-1, EDR_MAX_RISK + 1, 500])
def test_out_of_range_risk_is_rejected_rather_than_clamped(risk):
    with pytest.raises(ValueError, match="outside the observed"):
        severity_from_edr_risk(risk)


def test_severity_classes_order_from_low_to_critical():
    ranks = [severity.rank for severity in SeverityClass]
    assert ranks == sorted(ranks)
    assert max(SeverityClass, key=lambda s: s.rank) is SeverityClass.CRITICAL
