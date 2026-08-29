"""Monte Carlo aggregation of frequency and severity into loss metrics.

Draws a Poisson event count per attack type, samples the fitted severity for
each event, and aggregates the annual losses into AAL, VaR, TVaR and the
OEP/AEP exceedance curves. Every draw is vectorized and every source of
randomness takes an explicit seed or generator.
"""
