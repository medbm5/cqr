"""Fitting per attack type, the pooled fallback, and sampling."""

import numpy as np
import pytest
from helpers import incident

from risk_engine.attack_types import AttackType
from risk_engine.severity import (
    PeerWeightParams,
    fit_severity_model,
    load_incidents,
)
from risk_engine.severity.cleaning import CleaningReport


def cleaning_report(rows=0):
    """A minimal report, for tests that build incidents directly."""
    return CleaningReport(
        rows_read=rows,
        incidents=rows,
        rules=(),
        sector_repairs={},
        sector_labels_before=1,
        sector_labels_after=1,
        losses_missing=0,
        unknown_attack_types={},
    )


def population(attack_type, n, *, mu=11.0, sigma=1.5, sector="Retail", seed=1):
    """`n` incidents of one type, with losses drawn from a known lognormal."""
    rng = np.random.default_rng(seed)
    return [
        incident(
            f"inc-{attack_type.value}-{i}",
            attack_type=attack_type,
            sector=sector,
            loss=float(rng.lognormal(mean=mu, sigma=sigma)),
        )
        for i in range(n)
    ]


# ------------------------------------------------------------------- fitting


def test_each_attack_type_gets_its_own_fit_when_the_sample_supports_it():
    incidents = population(AttackType.RANSOMWARE, 200, mu=12.0, sigma=1.0) + population(
        AttackType.PHISHING, 200, mu=9.0, sigma=1.0, seed=2
    )

    model = fit_severity_model(incidents, cleaning_report(len(incidents)))

    ransomware = model.fits[AttackType.RANSOMWARE]
    phishing = model.fits[AttackType.PHISHING]
    assert not ransomware.used_pooled
    assert not phishing.used_pooled
    assert ransomware.params.mu == pytest.approx(12.0, abs=0.2)
    assert phishing.params.mu == pytest.approx(9.0, abs=0.2)
    # Segmentation is the point: pooling these two would price both wrongly.
    assert ransomware.params.median_eur > 10 * phishing.params.median_eur


def test_params_by_type_exposes_every_known_attack_type():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 100), cleaning_report(100))

    assert set(model.params_by_type) == set(AttackType)
    assert set(model.fit_diagnostics) == set(AttackType)


def test_diagnostics_are_attached_to_every_fit():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report(200))

    diagnostics = model.fit_diagnostics[AttackType.RANSOMWARE]
    assert diagnostics.observations == 200
    assert diagnostics.effective_n == pytest.approx(200.0)
    assert 0.0 <= diagnostics.weighted_ks <= 1.0
    assert len(diagnostics.qq_theoretical) == len(diagnostics.qq_empirical)


# ------------------------------------------------------------------ fallback


def test_a_thin_attack_type_falls_back_to_pooled_and_says_so():
    # 200 ransomware peers, but only 5 ddos: far below n_eff = 30.
    incidents = population(AttackType.RANSOMWARE, 200, mu=12.0) + population(
        AttackType.DDOS, 5, mu=8.0, seed=3
    )

    model = fit_severity_model(incidents, cleaning_report(len(incidents)))

    ddos = model.fits[AttackType.DDOS]
    assert ddos.used_pooled
    assert ddos.own_observations == 5
    assert ddos.own_effective_n < 30.0
    assert ddos.params == model.pooled.params


def test_the_fallback_threshold_is_a_parameter():
    incidents = population(AttackType.RANSOMWARE, 200) + population(AttackType.DDOS, 40, seed=3)

    strict = fit_severity_model(incidents, cleaning_report(), min_effective_n=100.0)
    lenient = fit_severity_model(incidents, cleaning_report(), min_effective_n=10.0)

    assert strict.fits[AttackType.DDOS].used_pooled
    assert not lenient.fits[AttackType.DDOS].used_pooled


def test_effective_sample_size_not_row_count_decides_the_fallback():
    """A type can have 40 rows and still be too thin to fit.

    Kish measures how *evenly* the weight is spread, not how large it is: 40
    uniformly discounted peers still count as 40. What collapses the effective
    sample is one close peer among many distant ones, because then the fit is
    really being driven by that single incident.
    """
    incidents = population(AttackType.RANSOMWARE, 300) + [
        incident(
            f"inc-ddos-{i}",
            attack_type=AttackType.DDOS,
            # One exact peer; the rest are remote on every axis at once.
            sector="Retail" if i == 0 else "Finance",
            size="ETI" if i == 0 else "PME",
            maturity=55.0 if i == 0 else 100.0,
            loss=50_000.0,
        )
        for i in range(40)
    ]

    model = fit_severity_model(incidents, cleaning_report())

    ddos = model.fits[AttackType.DDOS]
    assert ddos.own_observations == 40
    assert ddos.own_effective_n < 30.0  # the 39 remote peers barely count
    assert ddos.used_pooled


def test_uniform_discounting_does_not_shrink_the_effective_sample():
    """The other half of the same property, stated explicitly.

    Peers that are all equally distant are still 40 independent observations of
    that population, so the fallback does not trigger. This is a real
    consequence of the Kish definition and is easy to misread as a bug.
    """
    incidents = population(AttackType.RANSOMWARE, 300) + [
        incident(
            f"inc-ddos-{i}",
            attack_type=AttackType.DDOS,
            sector="Finance",
            size="PME",
            maturity=95.0,
            loss=50_000.0,
        )
        for i in range(40)
    ]

    model = fit_severity_model(incidents, cleaning_report())

    ddos = model.fits[AttackType.DDOS]
    assert ddos.own_effective_n == pytest.approx(40.0)
    assert not ddos.used_pooled


def test_a_type_with_no_incidents_uses_pooled_and_reports_a_zero_sample():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report(200))

    supply_chain = model.fits[AttackType.SUPPLY_CHAIN]
    assert supply_chain.used_pooled
    assert supply_chain.own_observations == 0
    assert supply_chain.own_effective_n == 0.0
    assert supply_chain.params == model.pooled.params


def test_fitting_needs_at_least_one_usable_loss():
    unusable = [incident("inc-1", loss=None)]

    with pytest.raises(ValueError, match="nothing to fit"):
        fit_severity_model(unusable, cleaning_report(1))


# ------------------------------------------------------------------ sampling


def test_sampling_is_deterministic_under_a_seed():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report(200))

    first = model.sample(AttackType.RANSOMWARE, 100, np.random.default_rng(42))
    second = model.sample(AttackType.RANSOMWARE, 100, np.random.default_rng(42))

    assert np.array_equal(first, second)


def test_different_seeds_give_different_draws():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report(200))

    first = model.sample(AttackType.RANSOMWARE, 100, np.random.default_rng(1))
    second = model.sample(AttackType.RANSOMWARE, 100, np.random.default_rng(2))

    assert not np.array_equal(first, second)


def test_samples_reproduce_the_fitted_distribution():
    model = fit_severity_model(
        population(AttackType.RANSOMWARE, 5_000, mu=11.0, sigma=1.5), cleaning_report()
    )
    params = model.params_by_type[AttackType.RANSOMWARE]

    draws = model.sample(AttackType.RANSOMWARE, 200_000, np.random.default_rng(0))

    assert float(np.median(draws)) == pytest.approx(params.median_eur, rel=0.05)
    assert float(np.mean(draws)) == pytest.approx(params.mean_eur, rel=0.10)
    assert bool(np.all(draws > 0.0))


def test_sampling_zero_losses_is_valid():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 100), cleaning_report())

    draws = model.sample(AttackType.RANSOMWARE, 0, np.random.default_rng(0))

    assert draws.shape == (0,)


def test_sampling_a_negative_count_is_rejected():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 100), cleaning_report())

    with pytest.raises(ValueError, match="negative number"):
        model.sample(AttackType.RANSOMWARE, -1, np.random.default_rng(0))


# --------------------------------------------------------------- explanation


def test_explanation_reports_samples_weights_parameters_and_euros():
    incidents = population(AttackType.RANSOMWARE, 200, mu=12.0) + population(
        AttackType.DDOS, 5, seed=3
    )

    model = fit_severity_model(incidents, cleaning_report(len(incidents)))
    text = "\n".join(model.to_explanation())

    assert "Retail sector, ETI, maturity 55/100" in text
    assert "w_sector x w_size x exp(-d^2 / 2h^2)" in text
    assert "No incident is discarded" in text
    assert "n_eff" in text
    assert "median EUR" in text and "mean EUR" in text
    assert "[n_eff < 30 -> pooled]" in text
    assert "weighted KS=" in text


def test_explanation_flags_a_type_with_no_incidents_of_its_own():
    model = fit_severity_model(population(AttackType.RANSOMWARE, 200), cleaning_report(200))

    assert "[no incidents of this type -> pooled]" in "\n".join(model.to_explanation())


# ----------------------------------------------------------------- real data


def test_the_case_data_fits_as_the_notebook_predicted(fixtures_dir):
    """The peer group is soft enough that no named type needs the fallback."""
    path = fixtures_dir.parent.parent.parent / "data" / "cyber_incidents.csv"
    if not path.exists():  # pragma: no cover - data is not vendored in every checkout
        pytest.skip("case data not present")

    incidents, cleaning = load_incidents(path)
    model = fit_severity_model(incidents, cleaning)

    assert model.incidents_fitted == 1598
    # Hard filtering to exact peers would leave 112 incidents and no usable
    # per-type cell; soft weighting keeps every named type above the threshold.
    named = [attack for attack in AttackType if attack is not AttackType.OTHER]
    assert all(not model.fits[attack].used_pooled for attack in named)
    assert model.pooled.own_effective_n > 1000.0

    # Ransomware and data breach must price well above phishing, as in the base.
    assert (
        model.params_by_type[AttackType.RANSOMWARE].median_eur
        > model.params_by_type[AttackType.PHISHING].median_eur
    )


def test_peer_params_change_the_fit(fixtures_dir):
    path = fixtures_dir.parent.parent.parent / "data" / "cyber_incidents.csv"
    if not path.exists():  # pragma: no cover - data is not vendored in every checkout
        pytest.skip("case data not present")

    incidents, cleaning = load_incidents(path)

    default = fit_severity_model(incidents, cleaning)
    sharp = fit_severity_model(
        incidents,
        cleaning,
        peer_params=PeerWeightParams(sector_other_weight=0.01, maturity_bandwidth=3.0),
    )

    # A sharper kernel concentrates weight on close peers, shrinking n_eff.
    assert sharp.pooled.own_effective_n < default.pooled.own_effective_n
    assert sharp.pooled.params.mu != default.pooled.params.mu


def test_explanation_reports_when_the_lognormal_beats_a_pareto_tail():
    # Data genuinely drawn from a lognormal: the rival tail should lose, and the
    # trace should say so rather than only ever warning.
    model = fit_severity_model(
        population(AttackType.RANSOMWARE, 3_000, mu=11.0, sigma=0.4), cleaning_report()
    )

    assert "lognormal beats a Pareto tail" in "\n".join(model.to_explanation())
