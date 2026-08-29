"""Annualized attack frequency, expressed in episodes rather than alerts.

Attack-grade events are clustered per asset into episodes separated by a
configurable session gap, then scaled to a yearly rate using the observed
telemetry window (``365 / observed_days``) — never a hardcoded horizon.
"""
