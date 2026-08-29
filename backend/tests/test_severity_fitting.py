"""Peer weighting arithmetic, weighted fitting, and parameter recovery."""

import math

import numpy as np
import pytest
from helpers import incident

from risk_engine.severity import (
    LognormalParams,
    PeerWeightParams,
    effective_sample_size,
    fit_lognormal,
    fit_pareto_tail,
    maturity_weight,
    peer_weight,
    peer_weights,
    qq_points,
    sector_weight,
    size_weight,
    weighted_ks,
    weighted_quantile,
)

# ------------------------------------------------------------------ weighting


def test_sector_and_size_weights_are_the_configured_constants():
    params = PeerWeightParams()

    assert sector_weight("Retail", params) == 1.0
    assert sector_weight("Finance", params) == 0.4
    assert size_weight("ETI", params) == 1.0
    assert size_weight("PME", params) == 0.6


def test_the_weights_are_parameters_not_constants():
    params = PeerWeightParams(
        target_sector="Finance",
        sector_other_weight=0.1,
        target_size="GE",
        size_other_weight=0.2,
    )

    assert sector_weight("Finance", params) == 1.0
    assert sector_weight("Retail", params) == 0.1
    assert size_weight("GE", params) == 1.0
    assert size_weight("ETI", params) == 0.2


def test_the_maturity_kernel_peaks_at_the_target_and_decays():
    params = PeerWeightParams(target_maturity=55.0, maturity_bandwidth=15.0)

    assert maturity_weight(55.0, params) == 1.0
    # exp(-d^2 / 2h^2), checked against the closed form.
    assert maturity_weight(70.0, params) == pytest.approx(math.exp(-(15**2) / (2 * 15**2)))
    assert maturity_weight(40.0, params) == pytest.approx(maturity_weight(70.0, params))
    assert maturity_weight(100.0, params) < maturity_weight(70.0, params)
    assert maturity_weight(100.0, params) > 0.0  # soft, never a hard cut


def test_a_narrower_bandwidth_sharpens_the_peer_group():
    far = 75.0
    wide = maturity_weight(far, PeerWeightParams(maturity_bandwidth=30.0))
    narrow = maturity_weight(far, PeerWeightParams(maturity_bandwidth=5.0))

    assert narrow < wide


def test_peer_weight_is_the_product_of_its_three_parts():
    params = PeerWeightParams()
    peer = incident(sector="Finance", size="PME", maturity=70.0)

    expected = 0.4 * 0.6 * maturity_weight(70.0, params)
    assert peer_weight(peer, params) == pytest.approx(expected)


def test_an_exact_peer_weighs_one():
    assert (
        peer_weight(incident(sector="Retail", size="ETI", maturity=55.0), PeerWeightParams()) == 1.0
    )


def test_a_mismatch_on_any_axis_discounts_the_whole_weight():
    params = PeerWeightParams()
    perfect = peer_weight(incident(), params)

    for mismatch in (
        incident(sector="Finance"),
        incident(size="PME"),
        incident(maturity=20.0),
    ):
        assert peer_weight(mismatch, params) < perfect


@pytest.mark.parametrize(
    "kwargs",
    [{"maturity_bandwidth": 0}, {"maturity_bandwidth": -1}, {"sector_other_weight": -0.1}],
)
def test_invalid_weighting_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        PeerWeightParams(**kwargs)


# ------------------------------------------------------- effective sample size


def test_kish_equals_the_row_count_when_weights_are_equal():
    assert effective_sample_size(np.ones(40)) == pytest.approx(40.0)
    assert effective_sample_size(np.full(40, 0.4)) == pytest.approx(40.0)


def test_kish_falls_when_weight_concentrates():
    spread = effective_sample_size(np.ones(100))
    concentrated = effective_sample_size(np.array([100.0] + [0.01] * 99))

    assert concentrated < spread
    assert concentrated == pytest.approx(1.0, abs=0.05)


def test_kish_is_zero_when_every_weight_is_zero():
    assert effective_sample_size(np.zeros(10)) == 0.0


def test_soft_weighting_keeps_more_information_than_a_hard_filter():
    """The argument for the whole approach, as arithmetic."""
    peers = [incident(sector="Retail" if i < 100 else "Finance") for i in range(1000)]
    weights = peer_weights(peers, PeerWeightParams())

    hard_filter_n = 100  # what keeping only Retail would leave
    assert effective_sample_size(weights) > hard_filter_n


# ---------------------------------------------------------------- fitting


def test_parameter_recovery_on_a_synthetic_lognormal():
    """Given data drawn from a known lognormal, the fit must find it back."""
    rng = np.random.default_rng(20260829)
    mu, sigma = 11.0, 1.9
    losses = rng.lognormal(mean=mu, sigma=sigma, size=200_000)

    fitted = fit_lognormal(losses, np.ones_like(losses))

    assert fitted.mu == pytest.approx(mu, abs=0.02)
    assert fitted.sigma == pytest.approx(sigma, abs=0.02)


def test_parameter_recovery_when_the_weights_select_a_subpopulation():
    """Weights must steer the fit, not merely rescale it.

    Two populations are mixed; only the second is weighted. The fit has to
    recover the second one's parameters, not the mixture's.
    """
    rng = np.random.default_rng(7)
    wanted = rng.lognormal(mean=12.0, sigma=1.0, size=50_000)
    ignored = rng.lognormal(mean=8.0, sigma=1.0, size=50_000)

    losses = np.concatenate([ignored, wanted])
    weights = np.concatenate([np.zeros(50_000), np.ones(50_000)])

    fitted = fit_lognormal(losses, weights)

    assert fitted.mu == pytest.approx(12.0, abs=0.02)
    assert fitted.sigma == pytest.approx(1.0, abs=0.02)


def test_implied_median_and_mean_follow_the_closed_form():
    params = LognormalParams(mu=11.0, sigma=2.0)

    assert params.median_eur == pytest.approx(math.exp(11.0))
    assert params.mean_eur == pytest.approx(math.exp(11.0 + 2.0**2 / 2))
    # The heavy tail: the average incident costs far more than the typical one.
    assert params.mean_eur > 7 * params.median_eur


@pytest.mark.parametrize(
    ("losses", "weights", "match"),
    [
        (np.array([1.0, 2.0]), np.array([1.0]), "must align"),
        (np.array([]), np.array([]), "zero observations"),
        (np.array([1.0, -5.0]), np.ones(2), "strictly positive"),
        (np.array([1.0, 2.0]), np.zeros(2), "positive value"),
    ],
)
def test_fitting_rejects_input_it_cannot_fit(losses, weights, match):
    with pytest.raises(ValueError, match=match):
        fit_lognormal(losses, weights)


# ------------------------------------------------------------- diagnostics


def test_weighted_ks_is_near_zero_for_data_from_the_fitted_distribution():
    rng = np.random.default_rng(11)
    losses = rng.lognormal(mean=10.0, sigma=1.5, size=20_000)
    params = fit_lognormal(losses, np.ones_like(losses))

    assert weighted_ks(losses, np.ones_like(losses), params) < 0.02


def test_weighted_ks_is_large_for_a_badly_wrong_fit():
    rng = np.random.default_rng(11)
    losses = rng.lognormal(mean=10.0, sigma=1.5, size=5_000)

    assert weighted_ks(losses, np.ones_like(losses), LognormalParams(mu=5.0, sigma=1.0)) > 0.5


def test_weighted_quantile_respects_the_weights():
    losses = np.array([1.0, 2.0, 3.0, 100.0])

    # With all the weight on the small values, the top quantile ignores the outlier.
    weights = np.array([1.0, 1.0, 1.0, 0.0])
    assert weighted_quantile(losses, weights, 0.99) == 3.0
    # With all the weight on the outlier, it is the whole distribution.
    assert weighted_quantile(losses, np.array([0.0, 0.0, 0.0, 1.0]), 0.5) == 100.0


def test_qq_points_line_up_for_a_well_fitted_sample():
    rng = np.random.default_rng(3)
    losses = rng.lognormal(mean=10.0, sigma=1.2, size=20_000)
    params = fit_lognormal(losses, np.ones_like(losses))

    theoretical, empirical = qq_points(losses, np.ones_like(losses), params)

    assert len(theoretical) == len(empirical) == 50
    assert list(theoretical) == sorted(theoretical)
    # Away from the extreme ends, a good fit traces the identity line closely.
    for expected, observed in zip(theoretical[5:-5], empirical[5:-5], strict=True):
        assert observed == pytest.approx(expected, abs=0.1)


def test_a_pareto_tail_wins_on_data_that_actually_has_one():
    rng = np.random.default_rng(5)
    body = rng.lognormal(mean=10.0, sigma=0.5, size=4_000)
    # A genuine power-law tail the lognormal cannot reach.
    heavy = 1e5 * (1.0 - rng.random(1_000)) ** (-1.0 / 1.2)
    losses = np.concatenate([body, heavy])
    weights = np.ones_like(losses)

    tail = fit_pareto_tail(losses, weights, fit_lognormal(losses, weights))

    assert tail is not None
    assert tail.pareto_fits_tail_better
    assert tail.alpha == pytest.approx(1.2, rel=0.25)


def test_no_tail_is_reported_when_there_are_too_few_exceedances():
    losses = np.array([1000.0, 2000.0, 3000.0, 50_000.0])

    assert fit_pareto_tail(losses, np.ones(4), fit_lognormal(losses, np.ones(4))) is None


def test_quantile_gives_the_loss_at_a_probability():
    params = LognormalParams(mu=11.0, sigma=2.0)

    assert params.quantile_eur(0.5) == pytest.approx(params.median_eur)
    assert params.quantile_eur(0.95) > params.quantile_eur(0.5)
    # The 99th percentile of a heavy-tailed fit dwarfs its own mean.
    assert params.quantile_eur(0.99) > params.mean_eur


def test_diagnostics_degrade_gracefully_when_every_weight_is_zero():
    losses = np.array([1000.0, 2000.0, 3000.0])
    zeros = np.zeros(3)
    params = LognormalParams(mu=7.0, sigma=1.0)

    # No weighted sample means no distance to measure and no quantile to take;
    # these return neutral values rather than dividing by zero.
    assert weighted_ks(losses, zeros, params) == 0.0
    assert weighted_quantile(losses, zeros, 0.9) == 1000.0


def test_no_tail_is_fitted_when_the_exceedances_carry_no_weight():
    # Every observation weighted out: there is no weighted sample to fit a tail to.
    losses = np.array([1000.0 * (i + 1) for i in range(100)])

    assert fit_pareto_tail(losses, np.zeros(100), LognormalParams(mu=7.0, sigma=1.0)) is None


def test_no_tail_is_fitted_when_the_lognormal_puts_no_mass_above_the_threshold():
    # A fit so far below the data that its survival at the threshold underflows
    # to zero. Conditioning on the tail would divide by it.
    rng = np.random.default_rng(4)
    losses = rng.lognormal(mean=10.0, sigma=1.0, size=500)

    absurd = LognormalParams(mu=-500.0, sigma=1.0)
    assert fit_pareto_tail(losses, np.ones(500), absurd) is None
