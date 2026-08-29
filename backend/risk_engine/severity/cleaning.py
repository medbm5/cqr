"""Reading and repairing the external incident base.

`cyber_incidents.csv` is what turns an attack count into euros, so a defect in it
propagates straight into the final loss. Two defects matter and both fail
silently: sector labels damaged by a double encoding, which split two sectors in
four and quietly shrink the peer pool, and a numeric sentinel standing in for a
missing loss, which reads as a perfectly valid float.

Every rule applied here is counted and reported. See
`notebooks/01_eda.ipynb` section 6 for the evidence behind each.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from risk_engine.attack_types import AttackType

#: Sector labels damaged by one round of cp1252/UTF-8 double encoding, and their
#: repairs.
#:
#: Thirteen rows carry a mangled spelling of a label that is correct everywhere
#: else - `Ã‰nergie` on 8 rows and `SantÃ©` on 5 - so the raw file shows nine
#: sector labels where there are seven sectors. Left alone they split `Énergie`
#: and `Santé` in two and shrink both peer pools.
#:
#: The table is explicit so that a reviewer can see exactly what was changed
#: without running anything. It is not guesswork: each entry is the exact result
#: of re-encoding the damaged text to cp1252 and decoding it as UTF-8, and a test
#: asserts that equivalence, so the table cannot drift from the transformation it
#: claims to represent.
SECTOR_MOJIBAKE: dict[str, str] = {
    "Ã‰nergie": "Énergie",
    "SantÃ©": "Santé",
}

#: Sentinel used in `financial_loss_eur` for an unreported loss.
#:
#: Any value at or below zero is treated as missing. The file uses -1 on 2 rows
#: and contains no zeros, but the rule is written as `<= 0` because a zero-euro
#: incident is not a thing the base records: an incident with no measured cost is
#: an incident whose cost was not measured. Imputing €0 would drag the fitted
#: mean down with fabricated evidence.
MISSING_LOSS_SENTINEL = 0.0


@dataclass(frozen=True, slots=True)
class Incident:
    """One incident from the external base, cleaned and typed.

    Attributes:
        incident_id: Identifier of the incident.
        company_id: The affected organisation. One organisation can appear more
            than once.
        occurred_on: Date of the incident.
        sector: Sector of the affected organisation, encoding repaired.
        company_size: Size band - `PME`, `ETI` or `GE`.
        employees: Headcount of the affected organisation.
        attack_type: What kind of attack it was.
        severity: The base's own severity label, kept for diagnostics. It is a
            different vocabulary from the telemetry's and is never mixed with it.
        security_maturity_score: Maturity of the affected organisation, 0-100.
        records_exposed: Records exposed, or `None` if unreported.
        downtime_hours: Downtime, or `None` if unreported.
        loss_eur: Financial loss in euros, or `None` if unreported. Never zero.
    """

    incident_id: str
    company_id: str
    occurred_on: date
    sector: str
    company_size: str
    employees: int
    attack_type: AttackType
    severity: str
    security_maturity_score: float
    records_exposed: float | None
    downtime_hours: float | None
    loss_eur: float | None


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    """How many rows one cleaning rule touched.

    Attributes:
        rule: Short identifier of the rule.
        description: What the rule does, and why.
        rows_affected: Rows it changed or flagged.
    """

    rule: str
    description: str
    rows_affected: int


@dataclass(frozen=True, slots=True)
class CleaningReport:
    """What the cleaning pass read, repaired and set aside.

    Attributes:
        rows_read: Rows in the CSV.
        incidents: Incidents emitted.
        rules: One outcome per rule applied, in the order applied.
        sector_repairs: Damaged label to repair count.
        sector_labels_before: Distinct sector labels before repair.
        sector_labels_after: Distinct sector labels after repair.
        losses_missing: Incidents whose loss is unusable for fitting.
        unknown_attack_types: Attack-type strings the vocabulary does not cover,
            with their row counts. Mapped to `OTHER` rather than dropped.
    """

    rows_read: int
    incidents: int
    rules: tuple[RuleOutcome, ...]
    sector_repairs: Mapping[str, int]
    sector_labels_before: int
    sector_labels_after: int
    losses_missing: int
    unknown_attack_types: Mapping[str, int]

    def to_explanation(self) -> list[str]:
        """Render the cleaning pass as a numbered, human-readable trace."""
        lines = [f"1. Read {self.rows_read:,} incident(s) from the external base."]
        for index, outcome in enumerate(self.rules, start=2):
            lines.append(
                f"{index}. {outcome.description} Rows affected: {outcome.rows_affected:,}."
            )
        lines.append(
            f"{len(self.rules) + 2}. Emitted {self.incidents:,} typed incident(s); "
            f"{self.incidents - self.losses_missing:,} carry a usable loss and are "
            f"eligible for fitting."
        )
        return lines


def repair_mojibake(text: str) -> str:
    """Undo one round of cp1252/UTF-8 double encoding.

    Used to *validate* `SECTOR_MOJIBAKE` rather than to replace it: the
    replacement table is what the pipeline applies, and this function is what
    proves the table correct. It fails on text that was never damaged, which is
    how clean and damaged labels are told apart.

    Args:
        text: A possibly double-encoded string.

    Returns:
        The repaired text, or the input unchanged when it was already clean.
    """
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def load_incidents(path: Path | str) -> tuple[tuple[Incident, ...], CleaningReport]:
    """Read and clean the external incident base.

    Args:
        path: Path to `cyber_incidents.csv`.

    Returns:
        The cleaned incidents and the report accounting for every rule applied.

    Raises:
        ValueError: If an expected column is missing.
    """
    frame = pd.read_csv(path)
    expected = [
        "incident_id",
        "company_id",
        "date",
        "sector",
        "company_size",
        "employees",
        "attack_type",
        "severity",
        "security_maturity_score",
        "records_exposed",
        "downtime_hours",
        "financial_loss_eur",
    ]
    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing expected column(s): {missing}")

    rows_read = len(frame)
    labels_before = frame.sector.nunique()

    # -- rule 1: repair double-encoded sector labels ------------------------
    repairs: Counter[str] = Counter()
    for damaged in SECTOR_MOJIBAKE:
        count = int(frame.sector.eq(damaged).sum())
        if count:
            repairs[damaged] = count
    sectors = frame.sector.replace(SECTOR_MOJIBAKE)
    labels_after = sectors.nunique()

    # -- rule 2: treat non-positive losses as unreported ---------------------
    raw_loss = pd.to_numeric(frame.financial_loss_eur, errors="coerce")
    unusable = raw_loss.isna() | raw_loss.le(MISSING_LOSS_SENTINEL)
    losses = raw_loss.where(~unusable)

    # -- rule 3: parse dates -------------------------------------------------
    dates = pd.to_datetime(frame.date, errors="coerce")
    unparsed_dates = int(dates.isna().sum())

    # -- rule 4: map attack types onto the shared vocabulary -----------------
    known = {member.value for member in AttackType}
    unknown_types = Counter(str(value) for value in frame.attack_type if str(value) not in known)

    incidents = tuple(
        Incident(
            incident_id=str(incident_id),
            company_id=str(company_id),
            occurred_on=occurred.date(),
            sector=str(sector),
            company_size=str(size),
            employees=int(employees),
            attack_type=(
                AttackType(str(attack_type)) if str(attack_type) in known else AttackType.OTHER
            ),
            severity=str(severity),
            security_maturity_score=float(maturity),
            records_exposed=None if pd.isna(records) else float(records),
            downtime_hours=None if pd.isna(downtime) else float(downtime),
            loss_eur=None if pd.isna(loss) else float(loss),
        )
        for incident_id, company_id, occurred, sector, size, employees, attack_type, (
            severity
        ), maturity, records, downtime, loss in zip(
            frame.incident_id.tolist(),
            frame.company_id.tolist(),
            dates.tolist(),
            sectors.tolist(),
            frame.company_size.tolist(),
            frame.employees.tolist(),
            frame.attack_type.tolist(),
            frame.severity.tolist(),
            frame.security_maturity_score.tolist(),
            frame.records_exposed.tolist(),
            frame.downtime_hours.tolist(),
            losses.tolist(),
            strict=True,
        )
        if not pd.isna(occurred)
    )

    report = CleaningReport(
        rows_read=rows_read,
        incidents=len(incidents),
        rules=(
            RuleOutcome(
                rule="sector_mojibake",
                description=(
                    "Repaired sector labels damaged by cp1252/UTF-8 double encoding, "
                    f"collapsing {labels_before} raw label(s) to {labels_after}."
                ),
                rows_affected=sum(repairs.values()),
            ),
            RuleOutcome(
                rule="missing_loss_sentinel",
                description=(
                    "Flagged financial_loss_eur <= 0 as unreported rather than as a "
                    "zero-euro loss; those incidents are excluded from fitting, never "
                    "imputed."
                ),
                rows_affected=int(unusable.sum()),
            ),
            RuleOutcome(
                rule="parse_dates",
                description="Parsed incident dates; rows with an unparseable date are dropped.",
                rows_affected=unparsed_dates,
            ),
            RuleOutcome(
                rule="attack_type_vocabulary",
                description=(
                    "Mapped attack_type onto the shared vocabulary; unrecognised "
                    "values become 'other' rather than being dropped."
                ),
                rows_affected=sum(unknown_types.values()),
            ),
        ),
        sector_repairs=dict(repairs),
        sector_labels_before=labels_before,
        sector_labels_after=labels_after,
        losses_missing=sum(1 for incident in incidents if incident.loss_eur is None),
        unknown_attack_types=dict(unknown_types),
    )
    return incidents, report
