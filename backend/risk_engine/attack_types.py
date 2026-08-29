"""The attack vocabulary shared across the engine.

Frequency counts attacks of each type from telemetry; severity prices them from
the external incident base. The two stages must agree on what the categories
*are*, so the vocabulary lives here rather than inside either of them. How
telemetry techniques map onto it is a frequency concern and stays in
`risk_engine.frequency.attack_types`.
"""

from __future__ import annotations

from enum import StrEnum


class AttackType(StrEnum):
    """Attack categories shared with the external incident base.

    The eight named types are exactly those present in `cyber_incidents.csv`.
    `OTHER` is the fallback for anything the engine cannot place among them; it
    is always reported rather than hidden, so a growing `OTHER` share is visible
    as a signal that a mapping needs revisiting.
    """

    PHISHING = "phishing"
    RANSOMWARE = "ransomware"
    CREDENTIAL_THEFT = "credential_theft"
    DATA_BREACH = "data_breach"
    MISCONFIGURATION = "misconfiguration"
    DDOS = "ddos"
    INSIDER_ERROR = "insider_error"
    SUPPLY_CHAIN = "supply_chain"
    OTHER = "other"
