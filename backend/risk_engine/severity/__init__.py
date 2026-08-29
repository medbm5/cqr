"""Loss severity distributions fitted on comparable external incidents.

Peers are selected by soft weighting (sector, size and maturity kernels) rather
than hard filtering, so the effective sample size is reported alongside every
fit and a per-attack-type fit falls back to the pooled fit when that sample is
too thin to be trusted.
"""
