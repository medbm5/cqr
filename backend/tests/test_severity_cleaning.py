"""Cleaning rules on the external incident base."""

import pytest

from risk_engine.attack_types import AttackType
from risk_engine.severity import SECTOR_MOJIBAKE, load_incidents, repair_mojibake

HEADER = (
    "incident_id,company_id,date,sector,company_size,employees,attack_type,"
    "severity,security_maturity_score,records_exposed,downtime_hours,financial_loss_eur\n"
)


def write(tmp_path, *rows):
    """Write a small incident CSV and return its path."""
    path = tmp_path / "incidents.csv"
    path.write_text(HEADER + "".join(rows), encoding="utf-8")
    return path


def row(
    incident_id="inc-1",
    sector="Retail",
    size="ETI",
    attack="ransomware",
    maturity=55,
    loss=100000,
    date="2024-01-15",
    employees=1200,
):
    return (
        f"{incident_id},ORG-1,{date},{sector},{size},{employees},{attack},"
        f"major,{maturity},100,5.0,{loss}\n"
    )


# ------------------------------------------------------------------ mojibake


def test_the_replacement_table_matches_the_encoding_round_trip():
    """The explicit table must be exactly what a cp1252/UTF-8 repair produces.

    The table is what the pipeline applies, because it is reviewable without
    running anything. This test is what stops it drifting into guesswork.
    """
    for damaged, repaired in SECTOR_MOJIBAKE.items():
        assert repair_mojibake(damaged) == repaired


def test_repairing_undamaged_text_leaves_it_alone():
    for clean in ("Retail", "Énergie", "Santé", "Tech/SaaS"):
        assert repair_mojibake(clean) == clean


def test_damaged_sector_labels_are_repaired_and_counted(tmp_path):
    path = write(
        tmp_path,
        row("inc-1", sector="Énergie"),
        row("inc-2", sector="Ã‰nergie"),
        row("inc-3", sector="SantÃ©"),
    )

    incidents, report = load_incidents(path)

    assert [incident.sector for incident in incidents] == ["Énergie", "Énergie", "Santé"]
    assert report.sector_repairs == {"Ã‰nergie": 1, "SantÃ©": 1}
    assert report.sector_labels_before == 3
    assert report.sector_labels_after == 2


def test_repairs_collapse_labels_that_would_split_a_peer_pool(tmp_path):
    path = write(tmp_path, row("inc-1", sector="Santé"), row("inc-2", sector="SantÃ©"))

    _, report = load_incidents(path)

    rule = next(rule for rule in report.rules if rule.rule == "sector_mojibake")
    assert rule.rows_affected == 1
    assert report.sector_labels_after == 1


# ------------------------------------------------------------------- losses


@pytest.mark.parametrize("loss", ["-1", "0", "-1000"])
def test_non_positive_losses_are_missing_never_zero(tmp_path, loss):
    path = write(tmp_path, row("inc-1", loss=loss))

    incidents, report = load_incidents(path)

    assert incidents[0].loss_eur is None
    assert report.losses_missing == 1
    rule = next(rule for rule in report.rules if rule.rule == "missing_loss_sentinel")
    assert rule.rows_affected == 1


def test_a_positive_loss_survives(tmp_path):
    incidents, report = load_incidents(write(tmp_path, row(loss=39066)))

    assert incidents[0].loss_eur == 39066.0
    assert report.losses_missing == 0


def test_an_unparseable_loss_is_missing_not_an_error(tmp_path):
    incidents, _ = load_incidents(write(tmp_path, row(loss="n/a")))

    assert incidents[0].loss_eur is None


# -------------------------------------------------------------------- dates


def test_dates_are_parsed(tmp_path):
    incidents, _ = load_incidents(write(tmp_path, row(date="2023-07-04")))

    assert incidents[0].occurred_on.isoformat() == "2023-07-04"


def test_rows_with_an_unparseable_date_are_dropped_and_counted(tmp_path):
    path = write(tmp_path, row("inc-1"), row("inc-2", date="not-a-date"))

    incidents, report = load_incidents(path)

    assert len(incidents) == 1
    assert report.rows_read == 2
    rule = next(rule for rule in report.rules if rule.rule == "parse_dates")
    assert rule.rows_affected == 1


# ------------------------------------------------------------- attack types


def test_attack_types_map_onto_the_shared_vocabulary(tmp_path):
    incidents, _ = load_incidents(write(tmp_path, row(attack="credential_theft")))

    assert incidents[0].attack_type is AttackType.CREDENTIAL_THEFT


def test_an_unknown_attack_type_becomes_other_and_is_reported(tmp_path):
    path = write(tmp_path, row("inc-1", attack="cryptojacking"))

    incidents, report = load_incidents(path)

    assert incidents[0].attack_type is AttackType.OTHER
    assert report.unknown_attack_types == {"cryptojacking": 1}


# ------------------------------------------------------------------- report


def test_a_missing_column_is_reported_by_name(tmp_path):
    path = tmp_path / "incidents.csv"
    path.write_text("incident_id,sector\ninc-1,Retail\n", encoding="utf-8")

    with pytest.raises(ValueError, match="financial_loss_eur"):
        load_incidents(path)


def test_the_report_explains_every_rule(tmp_path):
    path = write(tmp_path, row("inc-1", sector="Ã‰nergie"), row("inc-2", loss="-1"))

    _, report = load_incidents(path)
    lines = report.to_explanation()
    text = "\n".join(lines)

    assert lines[0].startswith("1. Read 2 incident(s)")
    assert "double encoding" in text
    assert "never imputed" in text
    assert "1 carry a usable loss" in text
    assert [line.split(".", 1)[0] for line in lines] == [str(i) for i in range(1, len(lines) + 1)]


def test_the_real_base_cleans_as_the_notebook_described(fixtures_dir):
    """Guards the two headline numbers from notebook section 6."""
    path = fixtures_dir.parent.parent.parent / "data" / "cyber_incidents.csv"
    if not path.exists():  # pragma: no cover - data is not vendored in every checkout
        pytest.skip("case data not present")

    incidents, report = load_incidents(path)

    assert report.rows_read == 1600
    assert sum(report.sector_repairs.values()) == 13
    assert report.sector_labels_before == 9
    assert report.sector_labels_after == 7
    assert report.losses_missing == 2
    assert len(incidents) == 1600
