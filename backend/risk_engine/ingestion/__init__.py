"""Loading and normalization of the raw inputs.

Responsibilities:

* read the SIEM, EDR and incident CSVs into typed frames;
* normalize severity onto a single 0-1 scale across feeds;
* repair the known encoding damage in the incident sector column and treat the
  ``-1`` loss sentinel as missing rather than as a zero-euro loss;
* deduplicate events observed in both telemetry feeds (same asset, same MITRE
  technique, same timestamp), keeping the worst observed severity.
"""
