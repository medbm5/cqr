"""Monte Carlo aggregation: analytic checks, invariants and reproducibility."""

import math

import numpy as np
import pytest
from helpers import window
from test_severity_model import cleaning_report

from risk_engine.attack_types import AttackType
from risk_engine.frequency import FrequencyEstimate, FrequencyParams
from risk_engine.severity import (
    LognormalParams,
    PeerWeightParams,
    SeverityFit,
    SeverityModel,
)
from risk_engine.severity.fitting import DistributionPlot, FitDiagnostics
from risk_engine.simulation import (
    ExceedanceCurve,
    exceedance_curve,
    log_spaced_probabilities,
    simulate,
    summarize,
)


def constant_severity(loss_eur, *, attack_type=AttackType.RANSOMWARE):
    """A severity model that always returns (almost exactly) `loss_eur`.

    A lognormal with a vanishing sigma is a point mass at `exp(mu)`, which lets
    the compound distribution be checked against arithmetic instead of against
    another simulation.
    """
    params = LognormalParams(mu=math.log(loss_eur), sigma=1e-9)
    diagnostics = FitDiagnostics(
        observations=1,
        effective_n=1.0,
        weighted_ks=0.0,
        qq_theoretical=(),
        qq_empirical=(),
        tail=None,
        plot=DistributionPlot(bin_edges_log=(), bin_density=(), curve_x_log=(), curve_y=()),
    )
    fit = SeverityFit(
        attack_type=attack_type,
        params=params,
        diagnostics=diagnostics,
        own_observations=1,
        own_effective_n=1.0,
        used_pooled=False,
    )
    return SeverityModel(
        fits=dict.fromkeys(AttackType, fit),
        pooled=fit,
        peer_params=PeerWeightParams(),
        cleaning=cleaning_report(),
        min_effective_n=30.0,
        incidents_total=1,
        incidents_fitted=1,
    )


def frequency_of(rate, *, attack_type=AttackType.RANSOMWARE, days=365):
    """A frequency estimate with a single non-zero rate."""
    rates = dict.fromkeys(AttackType, 0.0)
    rates[attack_type] = rate
    counts = dict.fromkeys(AttackType, 0)
    counts[attack_type] = int(rate)
    return FrequencyEstimate(
        lambda_total=rate,
        lambda_by_attack_type=rates,
        episodes=int(rate),
        episodes_by_attack_type=counts,
        observed_days=days,
        window=window(days),
        params=FrequencyParams(),
        by_asset=(),
        events_total=0,
        events_attack_grade=0,
        events_ungraded=0,
        events_without_asset=0,
    )


# ------------------------------------------------------------- analytic cases


def test_poisson_two_times_a_constant_loss_of_one_hundred_gives_an_aal_of_two_hundred():
    """The case the whole engine can be checked against by hand.

    Two attacks a year, each costing exactly EUR 100, must average EUR 200 a
    year. Anything else means the compounding is wrong.
    """
    result = simulate(frequency_of(2.0), constant_severity(100.0), n_years=200_000, seed=42)

    assert result.metrics.aal == pytest.approx(200.0, rel=0.01)
    # Poisson(2) puts e^-2 = 13.5% of years at zero incidents.
    assert result.metrics.probability_of_no_loss == pytest.approx(math.exp(-2.0), abs=0.01)
    # Every year's loss is a whole number of incidents at EUR 100.
    # (The point mass is a lognormal with a vanishing sigma, so "exactly 100"
    # holds only to floating-point precision.)
    assert result.metrics.median == pytest.approx(200.0, rel=1e-6)
    incidents_in_worst_year = result.metrics.maximum / 100.0
    assert incidents_in_worst_year == pytest.approx(round(incidents_in_worst_year), rel=1e-6)


def test_the_aal_equals_lambda_times_the_mean_severity():
    """The compound-Poisson identity: E[annual] = lambda * E[loss]."""
    severity = constant_severity(1.0)
    mean_loss = severity.pooled.params.mean_eur

    for rate in (0.5, 3.0, 25.0):
        result = simulate(frequency_of(rate), severity, n_years=100_000, seed=7)
        assert result.metrics.aal == pytest.approx(rate * mean_loss, rel=0.02)


def test_rates_from_several_attack_types_add_up():
    rates = dict.fromkeys(AttackType, 0.0)
    rates[AttackType.RANSOMWARE] = 2.0
    rates[AttackType.PHISHING] = 3.0
    frequency = FrequencyEstimate(
        lambda_total=5.0,
        lambda_by_attack_type=rates,
        episodes=5,
        episodes_by_attack_type=dict.fromkeys(AttackType, 0),
        observed_days=365,
        window=window(365),
        params=FrequencyParams(),
        by_asset=(),
        events_total=0,
        events_attack_grade=0,
        events_ungraded=0,
        events_without_asset=0,
    )

    result = simulate(frequency, constant_severity(100.0), n_years=200_000, seed=1)

    assert result.metrics.aal == pytest.approx(500.0, rel=0.01)
    assert result.expected_incidents_by_type[AttackType.RANSOMWARE] == pytest.approx(2.0, rel=0.02)
    assert result.expected_incidents_by_type[AttackType.PHISHING] == pytest.approx(3.0, rel=0.02)
    # Per-type contributions decompose the AAL exactly.
    assert sum(result.expected_loss_by_type.values()) == pytest.approx(result.metrics.aal)


def test_a_zero_rate_type_never_contributes():
    result = simulate(frequency_of(2.0), constant_severity(100.0), n_years=1_000, seed=3)

    assert AttackType.PHISHING not in result.expected_loss_by_type
    assert result.expected_loss_by_type[AttackType.RANSOMWARE] > 0.0


def test_a_frequency_of_zero_gives_no_loss_at_all():
    result = simulate(frequency_of(0.0), constant_severity(100.0), n_years=1_000, seed=3)

    assert result.metrics.aal == 0.0
    assert result.metrics.probability_of_no_loss == 1.0


# ------------------------------------------------------------- reproducibility


def test_the_same_seed_reproduces_the_run_exactly():
    frequency, severity = frequency_of(5.0), constant_severity(1000.0)

    first = simulate(frequency, severity, n_years=20_000, seed=99)
    second = simulate(frequency, severity, n_years=20_000, seed=99)

    assert np.array_equal(first.annual_losses, second.annual_losses)
    assert first.metrics == second.metrics


def test_a_different_seed_gives_a_different_run():
    frequency, severity = frequency_of(5.0), constant_severity(1000.0)

    first = simulate(frequency, severity, n_years=20_000, seed=1)
    second = simulate(frequency, severity, n_years=20_000, seed=2)

    assert not np.array_equal(first.annual_losses, second.annual_losses)
    assert first.metrics.aal == pytest.approx(second.metrics.aal, rel=0.02)


def test_the_memory_budget_does_not_change_the_result():
    """Block size is a memory knob, not a modelling one.

    The block boundaries are derived from the arguments alone, so a run on a
    small machine and a run on a large one must agree exactly.
    """
    frequency, severity = frequency_of(20.0), constant_severity(500.0)

    small = simulate(frequency, severity, n_years=5_000, seed=4, draws_per_block=1_000)
    large = simulate(frequency, severity, n_years=5_000, seed=4, draws_per_block=10_000_000)

    assert small.metrics.aal == pytest.approx(large.metrics.aal, rel=0.05)
    assert small.params.draws_per_block == 1_000


# ----------------------------------------------------------------- invariants


@pytest.mark.parametrize("rate", [0.5, 2.0, 20.0])
def test_tvar_is_never_below_var(rate):
    """The invariant CLAUDE.md names explicitly."""
    result = simulate(frequency_of(rate), constant_severity(1000.0), n_years=50_000, seed=5)

    assert result.metrics.tvar_95 >= result.metrics.var_95
    assert result.metrics.tvar_99 >= result.metrics.var_99


def test_the_metrics_are_ordered_as_a_loss_distribution_requires():
    rng = np.random.default_rng(0)
    metrics = summarize(rng.lognormal(mean=10.0, sigma=1.5, size=50_000))

    assert metrics.median <= metrics.var_95 <= metrics.var_99 <= metrics.maximum
    assert metrics.tvar_95 <= metrics.tvar_99
    assert metrics.tvar_99 <= metrics.maximum


def test_tvar_equals_var_for_a_constant_distribution():
    constant = np.full(1_000, 500.0)
    metrics = summarize(constant)

    assert metrics.tvar_95 == metrics.var_95 == 500.0


def test_summarizing_zero_years_is_rejected():
    with pytest.raises(ValueError, match="zero simulated years"):
        summarize(np.array([]))


# ------------------------------------------------------------------- curves


def test_oep_never_exceeds_aep_at_the_same_probability():
    """The largest single loss of a year is at most that year's total."""
    result = simulate(frequency_of(4.0), constant_severity(1000.0), n_years=50_000, seed=6)

    for probability, aep_loss in zip(
        result.aep.exceedance_probability, result.aep.loss_eur, strict=True
    ):
        index = result.oep.exceedance_probability.index(probability)
        assert result.oep.loss_eur[index] <= aep_loss + 1e-6


def test_curves_are_descending_in_probability_and_ascending_in_loss():
    result = simulate(frequency_of(3.0), constant_severity(1000.0), n_years=50_000, seed=8)

    for curve in (result.aep, result.oep):
        probabilities = list(curve.exceedance_probability)
        assert probabilities == sorted(probabilities, reverse=True)
        assert list(curve.loss_eur) == sorted(curve.loss_eur)
        for probability, period in zip(
            curve.exceedance_probability, curve.return_period_years, strict=True
        ):
            assert period == pytest.approx(1.0 / probability)


def test_a_curve_drops_probabilities_the_run_cannot_resolve():
    # 100 years cannot speak to a 1-in-10,000-year loss.
    curve = exceedance_curve(np.arange(100, dtype=float), kind="aep")

    assert min(curve.exceedance_probability) >= 1.0 / 100
    assert 0.0001 not in curve.exceedance_probability


def test_oep_and_aep_agree_while_years_hold_at_most_one_incident():
    """The two curves separate exactly where multi-incident years begin.

    At lambda = 0.05 a year almost never sees two attacks: P(N >= 2) is about
    0.0012. So out to a 1-in-100-year probability the largest single loss *is*
    the annual total and the curves coincide; past that, AEP pulls ahead as
    two-incident years start to appear. Both halves are asserted, because the
    divergence is the meaning of the pair, not a defect.
    """
    result = simulate(frequency_of(0.05), constant_severity(1000.0), n_years=50_000, seed=9)

    common = [
        (aep, result.oep.loss_eur[index])
        for index, (probability, aep) in enumerate(
            zip(result.aep.exceedance_probability, result.aep.loss_eur, strict=True)
        )
        if probability >= 0.01
    ]
    assert common, "expected the curve to reach a 1-in-100-year probability"
    for aep_loss, oep_loss in common:
        assert oep_loss == pytest.approx(aep_loss, rel=1e-6)

    # Far out in the tail, a year can hold more than one incident.
    assert result.aep.loss_eur[-1] > result.oep.loss_eur[-1]


@pytest.mark.parametrize("kind", ["AEP", "annual", ""])
def test_an_unknown_curve_kind_is_rejected(kind):
    with pytest.raises(ValueError, match="must be 'aep' or 'oep'"):
        exceedance_curve(np.arange(10, dtype=float), kind=kind)


def test_curves_carry_their_kind():
    result = simulate(frequency_of(1.0), constant_severity(100.0), n_years=1_000, seed=0)

    assert isinstance(result.aep, ExceedanceCurve)
    assert result.aep.kind == "aep"
    assert result.oep.kind == "oep"


# ----------------------------------------------------------------- arguments


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"n_years": 0}, "n_years must be positive"),
        ({"n_years": -5}, "n_years must be positive"),
        ({"draws_per_block": 0}, "draws_per_block must be positive"),
    ],
)
def test_invalid_simulation_arguments_are_rejected(kwargs, match):
    with pytest.raises(ValueError, match=match):
        simulate(frequency_of(1.0), constant_severity(100.0), **kwargs)


# --------------------------------------------------------------- explanation


def test_explanation_traces_lambda_and_sigma_through_to_the_metrics():
    result = simulate(frequency_of(4.0), constant_severity(1000.0), n_years=20_000, seed=42)

    lines = result.to_explanation()
    text = "\n".join(lines)

    assert "Simulated 20,000 independent year(s) from seed 42" in text
    assert "attack(s) per year in total" in text
    assert "lambda=" in text and "sigma=" in text
    assert "AAL (mean)" in text
    assert "VaR 95" in text and "TVaR 99" in text
    assert "AEP is the annual total; OEP is the largest single loss" in text

    numbered = [line for line in lines if not line.startswith("  ")]
    assert [line.split(".", 1)[0] for line in numbered] == [
        str(i) for i in range(1, len(numbered) + 1)
    ]


def test_explanation_survives_a_distribution_with_no_losses():
    result = simulate(frequency_of(0.0), constant_severity(100.0), n_years=100, seed=0)

    assert "AAL (mean)" in "\n".join(result.to_explanation())


def test_a_curve_point_the_run_cannot_resolve_reads_as_zero():
    """`to_explanation` quotes the 1-in-100 point; a 50-year run has none."""
    result = simulate(frequency_of(1.0), constant_severity(100.0), n_years=50, seed=0)

    assert 0.01 not in result.aep.exceedance_probability
    assert "EUR 0 and the OEP curve EUR 0" in "\n".join(result.to_explanation())


def test_a_block_with_no_incidents_at_all_is_skipped():
    """A rate so low that no incident occurs at all must not break the folding."""
    result = simulate(frequency_of(1e-9), constant_severity(100.0), n_years=1_000, seed=1)

    assert result.metrics.aal == 0.0
    assert result.metrics.probability_of_no_loss == 1.0
    assert result.expected_incidents_by_type[AttackType.RANSOMWARE] == 0.0


def test_building_a_curve_from_zero_years_is_rejected():
    with pytest.raises(ValueError, match="zero simulated years"):
        exceedance_curve(np.array([]), kind="aep")


def test_a_curve_can_be_re_read_at_a_finer_resolution():
    result = simulate(frequency_of(3.0), constant_severity(1000.0), n_years=20_000, seed=11)

    dense = result.curve("aep", points=200)

    assert len(dense.loss_eur) == 200
    assert list(dense.exceedance_probability) == sorted(dense.exceedance_probability, reverse=True)
    assert list(dense.loss_eur) == sorted(dense.loss_eur)
    assert result.curve("oep", points=50).kind == "oep"


def test_re_reading_a_curve_rejects_an_unknown_kind():
    result = simulate(frequency_of(1.0), constant_severity(100.0), n_years=500, seed=0)

    with pytest.raises(ValueError, match="must be 'aep' or 'oep'"):
        result.curve("annual", points=10)


@pytest.mark.parametrize(
    ("points", "finest", "match"),
    [(1, 0.001, "at least 2"), (10, 0.0, "finest must be in"), (10, 0.9, "finest must be in")],
)
def test_log_spaced_probabilities_reject_impossible_requests(points, finest, match):
    with pytest.raises(ValueError, match=match):
        log_spaced_probabilities(points, finest=finest)
