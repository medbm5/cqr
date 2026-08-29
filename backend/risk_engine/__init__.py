"""Citalid risk engine: quantify a company's annualized cyber loss.

Pure Python package — it never imports Django, never performs I/O beyond the
explicit loaders in :mod:`risk_engine.ingestion`, and holds no module-level
mutable state. It is runnable standalone from a CLI or a notebook so that every
figure surfaced by the API or the frontend can be reproduced without a server.

Pipeline stages, in order:

1. :mod:`risk_engine.ingestion` — load and normalize SIEM/EDR telemetry and the
   external incident base, then deduplicate events seen in both feeds.
2. :mod:`risk_engine.frequency` — annualized attack frequency, counted in
   episodes rather than raw alerts.
3. :mod:`risk_engine.severity` — loss distribution fitted on soft-weighted peer
   incidents.
4. :mod:`risk_engine.simulation` — Monte Carlo aggregation into AAL, VaR, TVaR
   and the OEP/AEP curves.
5. :mod:`risk_engine.explain` — audit trail turning any output back into the
   inputs and parameters that produced it.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
