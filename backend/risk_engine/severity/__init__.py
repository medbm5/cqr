"""Loss severity distributions fitted on comparable external incidents.

The chain is: clean the incident base, weight every incident by how much it
resembles the target company, fit a lognormal per attack type on the log scale,
and challenge each fit before trusting it.

Peers are selected by **soft weighting**, not hard filtering. Filtering to exact
matches keeps 112 of 1,598 incidents and leaves zero of eight attack types with a
credible sample (`notebooks/01_eda.ipynb` section 8), so every incident instead
contributes in proportion to its similarity, and every fit reports the Kish
effective sample size behind it. Below `DEFAULT_MIN_EFFECTIVE_N` a per-type fit
falls back to the pooled one and says so.

Typical use::

    incidents, cleaning = load_incidents(data_dir / "cyber_incidents.csv")
    model = fit_severity_model(incidents, cleaning)

    rng = np.random.default_rng(42)
    losses = model.sample(AttackType.RANSOMWARE, 1_000, rng)

    for line in model.to_explanation():
        print(line)
"""

from .cleaning import (
    MISSING_LOSS_SENTINEL,
    SECTOR_MOJIBAKE,
    CleaningReport,
    Incident,
    RuleOutcome,
    load_incidents,
    repair_mojibake,
)
from .fitting import (
    FitDiagnostics,
    LognormalParams,
    ParetoTail,
    diagnose,
    fit_lognormal,
    fit_pareto_tail,
    qq_points,
    weighted_ks,
    weighted_quantile,
)
from .model import (
    DEFAULT_MIN_EFFECTIVE_N,
    SeverityFit,
    SeverityModel,
    fit_severity_model,
)
from .peers import (
    PeerWeightParams,
    effective_sample_size,
    maturity_weight,
    peer_weight,
    peer_weights,
    sector_weight,
    size_weight,
)

__all__ = [
    "DEFAULT_MIN_EFFECTIVE_N",
    "MISSING_LOSS_SENTINEL",
    "SECTOR_MOJIBAKE",
    "CleaningReport",
    "FitDiagnostics",
    "Incident",
    "LognormalParams",
    "ParetoTail",
    "PeerWeightParams",
    "RuleOutcome",
    "SeverityFit",
    "SeverityModel",
    "diagnose",
    "effective_sample_size",
    "fit_lognormal",
    "fit_pareto_tail",
    "fit_severity_model",
    "load_incidents",
    "maturity_weight",
    "peer_weight",
    "peer_weights",
    "qq_points",
    "repair_mojibake",
    "sector_weight",
    "size_weight",
    "weighted_ks",
    "weighted_quantile",
]
