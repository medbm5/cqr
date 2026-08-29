"""Translation from MITRE ATT&CK techniques to the attack types losses are priced in.

Frequency is estimated per attack type because that is the only vocabulary the
two halves of the model share: the telemetry speaks in ATT&CK techniques, the
external incident base in attack types. This module is the single place the two
are reconciled, so a disputed attribution is one line to change and one place to
review.

The mapping is a modeling judgment, not a lookup of published fact - ATT&CK
techniques are steps in an intrusion, while the incident base classifies whole
campaigns. It was reviewed and approved by hand; the four calls that are genuinely
arguable are marked below.
"""

from __future__ import annotations

from enum import StrEnum


class AttackType(StrEnum):
    """Attack vocabulary shared with the external incident base.

    The eight named types are exactly those present in `cyber_incidents.csv`.
    `OTHER` is the fallback for techniques with no defensible home among them; it
    is reported rather than hidden, so a growing `OTHER` share is visible as a
    signal that the mapping needs revisiting.
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


#: Every technique observed in the case telemetry, mapped to an attack type.
#:
#: Attack-grade event counts are given per technique so the weight behind each
#: attribution is visible. Four entries are marked ARGUABLE: they are the ones
#: where a competent analyst could reasonably choose a different type, and they
#: are the first place to look if the frequency mix looks wrong.
TECHNIQUE_TO_ATTACK_TYPE: dict[str, AttackType] = {
    # -- Ransomware: encryption, recovery inhibition and the service teardown
    #    that precedes both.
    "T1486": AttackType.RANSOMWARE,  # Data Encrypted for Impact          (937)
    "T1490": AttackType.RANSOMWARE,  # Inhibit System Recovery            (998)
    "T1489": AttackType.RANSOMWARE,  # Service Stop        ARGUABLE: ddos (976)
    # -- Data breach: the exfiltration channels, and collection from the host.
    "T1020": AttackType.DATA_BREACH,  # Automated Exfiltration            (665)
    "T1041": AttackType.DATA_BREACH,  # Exfiltration Over C2 Channel      (660)
    "T1567": AttackType.DATA_BREACH,  # Exfiltration Over Web Service     (649)
    "T1005": AttackType.DATA_BREACH,  # Data from Local System             (10)
    # -- Credential theft: obtaining, cracking or reusing credentials.
    "T1003": AttackType.CREDENTIAL_THEFT,  # OS Credential Dumping        (596)
    "T1110": AttackType.CREDENTIAL_THEFT,  # Brute Force                  (586)
    # ARGUABLE: misconfiguration - the exposure is a config error, but what the
    # attacker does with it is credential theft.
    "T1552": AttackType.CREDENTIAL_THEFT,  # Unsecured Credentials        (593)
    "T1078": AttackType.CREDENTIAL_THEFT,  # Valid Accounts                (15)
    # -- Denial of service, network and endpoint.
    "T1498": AttackType.DDOS,  # Network Denial of Service                (760)
    "T1499": AttackType.DDOS,  # Endpoint Denial of Service               (750)
    # -- Phishing: the lure and the user action that completes it.
    "T1566": AttackType.PHISHING,  # Phishing                             (534)
    # ARGUABLE: other - user execution is the payload step of a phishing chain,
    # and the incident base would have classified the whole chain as phishing.
    "T1204": AttackType.PHISHING,  # User Execution                       (533)
    # -- Exploitation of exposed or unpatched services. The weakest attribution
    #    in this table: none of the eight types covers vulnerability
    #    exploitation, and an exposed service is the closest neighbour.
    # ARGUABLE: other, for both.
    "T1190": AttackType.MISCONFIGURATION,  # Exploit Public-Facing App    (337)
    "T1210": AttackType.MISCONFIGURATION,  # Exploitation of Remote Svcs  (338)
    # -- Reconnaissance and discovery. These are not attacks in the sense the
    #    incident base prices, and together they are 0.5% of attack-grade
    #    volume, so the fallback costs almost nothing.
    "T1592": AttackType.OTHER,  # Gather Victim Host Information           (20)
    "T1595": AttackType.OTHER,  # Active Scanning                          (11)
    "T1046": AttackType.OTHER,  # Network Service Discovery                (16)
    "T1087": AttackType.OTHER,  # Account Discovery                         (6)
}

#: Attack types the telemetry cannot observe at all.
#:
#: Neither has a corresponding ATT&CK technique in the feeds, so both receive a
#: frequency of zero from this stage - not because the risk is zero, but because
#: a SIEM and an EDR do not detect them. The incident base nonetheless records 78
#: supply-chain and 129 insider-error incidents. Anything downstream that treats
#: a zero here as "no exposure" is drawing a conclusion the data does not
#: support; the zero means "unobservable", and is surfaced in the explanation.
UNOBSERVABLE_ATTACK_TYPES: frozenset[AttackType] = frozenset(
    {AttackType.SUPPLY_CHAIN, AttackType.INSIDER_ERROR}
)


def attack_type_for(technique: str | None) -> AttackType:
    """Classify a MITRE technique into an attack type.

    Args:
        technique: An ATT&CK technique identifier, or `None` when the feed did
            not report one.

    Returns:
        The mapped attack type, or `AttackType.OTHER` when the technique is
        unknown or absent. An unmapped technique is a fallback rather than an
        error: a new detection rule upstream should not stop the pipeline, but
        it must show up in the report so the mapping can be extended.
    """
    if technique is None:
        return AttackType.OTHER
    return TECHNIQUE_TO_ATTACK_TYPE.get(technique, AttackType.OTHER)
