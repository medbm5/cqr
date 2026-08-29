"""Endpoint tests.

These exercise the HTTP contract, not the modelling: the figures are asserted
against the engine's own output rather than against hardcoded numbers, so a
deliberate model change breaks the engine tests that argue for it, and not these.
"""

import pytest
from rest_framework.test import APIClient

from api import pipeline

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def client():
    """A DRF client. The dataset is loaded once per process by the pipeline cache."""
    return APIClient()


@pytest.fixture(scope="module")
def dataset():
    """The cached dataset, so tests can compare responses against the engine."""
    if not (pipeline.data_dir() / "cyber_incidents.csv").exists():  # pragma: no cover
        pytest.skip("case data not present")
    return pipeline.get_dataset()


# --------------------------------------------------------------------- health


def test_health_reports_the_engine_version(client):
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["engine_version"]


# --------------------------------------------------------------------- assets


def test_assets_lists_the_estate_with_its_attack_activity(client, dataset):
    response = client.get("/api/assets/")

    assert response.status_code == 200
    body = response.json()
    assert len(body["assets"]) == len(dataset.assets)

    first = body["assets"][0]
    assert set(first) == {
        "asset_id",
        "asset_type",
        "business_criticality",
        "environment",
        "episodes",
        "annual_rate",
        "episodes_by_attack_type",
        "episodes_by_week",
    }
    # Weekly buckets exist for the heatmap and account for the asset's episodes.
    assert sum(first["episodes_by_week"].values()) == first["episodes"]
    # Sorted by descending episode count, as the engine returns them.
    counts = [asset["episodes"] for asset in body["assets"]]
    assert counts == sorted(counts, reverse=True)
    assert sum(counts) == sum(body["episodes_by_criticality"].values())


def test_assets_echoes_the_conventions_it_used(client, dataset):
    response = client.get("/api/assets/?severity_threshold=critical&session_window_hours=72")

    assert response.status_code == 200
    assert response.json()["params"] == {
        "severity_threshold": "critical",
        "session_window_hours": 72.0,
    }


def test_a_stricter_threshold_admits_fewer_attack_grade_events(client, dataset):
    """Stricter means fewer *events*. Episode counts are not monotone.

    Under asset-only clustering a looser threshold admits more events, which
    chain into longer episodes - so lowering the threshold can *reduce* the
    episode count while raising the event count. Asserting on episodes would
    encode an intuition the model does not have.
    """
    lenient = client.get("/api/frequency/?severity_threshold=medium").json()
    strict = client.get("/api/frequency/?severity_threshold=critical").json()

    assert strict["events_attack_grade"] < lenient["events_attack_grade"]
    # Whichever way the episode count moves, the incident rate is anchored
    # externally and does not move with the threshold at all.
    assert strict["lambda_incident"] == pytest.approx(lenient["lambda_incident"])


# ------------------------------------------------------------------ telemetry


def test_telemetry_summary_accounts_for_every_row(client, dataset):
    response = client.get("/api/telemetry/summary/")

    assert response.status_code == 200
    body = response.json()
    report = body["normalization"]

    assert report["rows_read"] == dataset.ingestion.report.rows_read
    assert report["total_events"] == dataset.ingestion.report.total_events
    assert report["events_in_both_feeds"] == dataset.ingestion.report.events_in_both_feeds
    assert len(report["feeds"]) == 2
    assert {feed["source"] for feed in report["feeds"]} == {"siem", "edr"}
    assert report["explanation"]


def test_telemetry_weekly_buckets_sum_to_the_event_total(client, dataset):
    body = client.get("/api/telemetry/summary/").json()
    weekly = body["summary"]["weekly"]

    assert sum(week["merged"] for week in weekly) == dataset.ingestion.report.total_events
    for week in weekly:
        assert week["siem_only"] + week["edr_only"] + week["both"] == week["merged"]
    starts = [week["week_start"] for week in weekly]
    assert starts == sorted(starts)


def test_telemetry_reports_the_severity_and_technique_mix(client, dataset):
    summary = client.get("/api/telemetry/summary/").json()["summary"]

    assert sum(summary["severity_mix"].values()) == dataset.ingestion.report.total_events
    assert set(summary["events_by_source"]) <= {"siem", "edr", "both"}
    assert summary["techniques"]


# ------------------------------------------------------------------ frequency


def test_frequency_returns_rates_and_the_trace(client, dataset):
    response = client.get("/api/frequency/")

    assert response.status_code == 200
    body = response.json()
    engine = pipeline.get_frequency(pipeline.DEFAULT_THRESHOLD, pipeline.DEFAULT_WINDOW_HOURS)

    assert body["lambda_detected"] == pytest.approx(engine.lambda_detected)
    # The rate the simulation prices is the *incident* rate, not the detection
    # rate, and the API must expose both so the two are never confused.
    assert body["lambda_incident"] == pytest.approx(engine.lambda_incident)
    assert body["lambda_incident"] < body["lambda_detected"]
    assert body["calibration"]["p_materialize"] > 0
    assert body["episodes"] == engine.episodes
    assert body["observed_days"] == engine.observed_days
    assert body["params"] == {"severity_threshold": "high", "session_window_hours": 24.0}
    assert body["explanation"]
    # Every attack type is present, including those the telemetry cannot observe.
    assert body["lambda_detected_by_attack_type"]["supply_chain"] == 0.0
    assert sum(body["lambda_detected_by_attack_type"].values()) == pytest.approx(
        body["lambda_detected"]
    )
    assert sum(body["lambda_incident_by_attack_type"].values()) == pytest.approx(
        body["lambda_incident"]
    )


def test_frequency_honours_the_query_parameters(client, dataset):
    wide = client.get("/api/frequency/?session_window_hours=72").json()
    narrow = client.get("/api/frequency/?session_window_hours=8").json()

    assert wide["episodes"] < narrow["episodes"]
    # The incident rate is anchored externally, so widening the window changes
    # how many attacks were detected, not how often losses occur.
    assert wide["lambda_incident"] == pytest.approx(narrow["lambda_incident"])
    assert wide["params"]["session_window_hours"] == 72.0


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ("?severity_threshold=extreme", "severity_threshold must be one of"),
        ("?session_window_hours=soon", "must be a number"),
        ("?session_window_hours=0", "must be positive"),
        ("?session_window_hours=-4", "must be positive"),
    ],
)
def test_frequency_rejects_bad_parameters(client, query, message):
    response = client.get(f"/api/frequency/{query}")

    assert response.status_code == 400
    assert message in response.json()["detail"]


# ------------------------------------------------------------------- severity


def test_severity_returns_a_fit_per_attack_type_with_plot_data(client, dataset):
    response = client.get("/api/severity/")

    assert response.status_code == 200
    body = response.json()

    assert len(body["fits"]) == len(dataset.severity.fits)
    assert body["incidents_fitted"] == dataset.severity.incidents_fitted
    assert body["peer_weighting"]["target_sector"] == "Retail"
    assert body["explanation"]

    ransomware = next(fit for fit in body["fits"] if fit["attack_type"] == "ransomware")
    assert ransomware["mean_eur"] > ransomware["median_eur"]  # heavy tail
    assert ransomware["observations"] > 0
    assert not ransomware["used_pooled"]

    plot = ransomware["diagnostics"]["plot"]
    assert len(plot["bin_edges_log"]) == len(plot["bin_density"]) + 1
    assert len(plot["curve_x_log"]) == len(plot["curve_y"])
    diagnostics = ransomware["diagnostics"]
    assert len(diagnostics["qq_theoretical"]) == len(diagnostics["qq_empirical"])


def test_severity_marks_a_type_that_fell_back_to_pooled(client, dataset):
    body = client.get("/api/severity/").json()

    other = next(fit for fit in body["fits"] if fit["attack_type"] == "other")
    assert other["used_pooled"]
    assert other["observations"] == 0


# ----------------------------------------------------------------- simulation


def test_simulate_returns_metrics_curves_and_the_chain(client, dataset):
    response = client.post(
        "/api/simulate/",
        {"n_years": 2_000, "seed": 7, "curve_points": 50, "include_sensitivity": False},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()

    metrics = body["metrics"]
    assert metrics["aal"] > 0
    assert metrics["tvar_95"] >= metrics["var_95"]
    assert metrics["tvar_99"] >= metrics["var_99"]
    assert body["n_years"] == 2_000
    assert body["seed"] == 7
    assert body["sensitivity"] is None
    assert body["explanation"]

    for curve in (body["aep_curve"], body["oep_curve"]):
        assert len(curve["loss_eur"]) == len(curve["exceedance_probability"])
        assert len(curve["loss_eur"]) <= 50
        assert curve["loss_eur"] == sorted(curve["loss_eur"])
    assert body["aep_curve"]["kind"] == "aep"
    assert body["oep_curve"]["kind"] == "oep"

    # The distribution behind the metrics, binned for a chart. Zero-loss years
    # ride alongside the bins rather than inside them, so the two must account
    # for the run between them.
    histogram = body["histogram"]
    assert len(histogram["bin_edges_eur"]) == len(histogram["counts"]) + 1
    assert sum(histogram["counts"]) == histogram["loss_years"]
    assert histogram["loss_years"] + histogram["zero_years"] == body["n_years"]
    assert histogram["scale"] == "log"

    # The plausibility cap, and what it cost.
    cap = body["loss_cap"]
    assert cap["cap_eur"] > 0
    assert cap["draws_capped"] <= cap["draws_total"]
    assert cap["aal_uncapped"] >= body["metrics"]["aal"]


def test_simulate_uses_documented_defaults(client, dataset):
    response = client.post("/api/simulate/", {"include_sensitivity": False}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["n_years"] == pipeline.DEFAULT_YEARS
    assert body["seed"] == 42
    assert body["params"] == {"severity_threshold": "high", "session_window_hours": 24.0}


def test_simulate_accepts_an_explicit_loss_cap(client, dataset):
    """The cap is a caller-visible modeling choice, not a hidden constant."""
    payload = {"n_years": 2_000, "seed": 3, "include_sensitivity": False, "loss_cap_eur": 100_000.0}

    body = client.post("/api/simulate/", payload, format="json").json()

    assert body["loss_cap"]["cap_eur"] == 100_000.0
    # Supplied rather than read off a quantile, and the response says which.
    assert body["loss_cap"]["quantile"] is None
    assert body["loss_cap"]["draws_capped"] > 0


def test_the_default_loss_cap_is_read_off_the_peer_losses(client, dataset):
    body = client.post(
        "/api/simulate/", {"n_years": 1_000, "include_sensitivity": False}, format="json"
    ).json()

    assert body["loss_cap"]["quantile"] == pytest.approx(0.999)
    assert body["loss_cap"]["cap_eur"] > 0


def test_a_non_positive_loss_cap_is_rejected(client, dataset):
    response = client.post(
        "/api/simulate/", {"loss_cap_eur": 0.0, "include_sensitivity": False}, format="json"
    )

    assert response.status_code == 400
    assert "loss_cap_eur" in response.json()


def test_the_loss_cap_is_part_of_the_cache_key(client, dataset):
    """Two caps are two answers; serving one from the other's cache would lie."""
    base = {"n_years": 2_000, "seed": 3, "include_sensitivity": False}

    tight = client.post("/api/simulate/", base | {"loss_cap_eur": 50_000.0}, format="json").json()
    loose = client.post("/api/simulate/", base | {"loss_cap_eur": 5e9}, format="json").json()

    assert tight["metrics"]["aal"] < loose["metrics"]["aal"]


def test_simulate_is_reproducible_for_the_same_request(client, dataset):
    payload = {"n_years": 1_000, "seed": 3, "include_sensitivity": False}

    first = client.post("/api/simulate/", payload, format="json").json()
    second = client.post("/api/simulate/", payload, format="json").json()

    assert first["metrics"] == second["metrics"]


def test_simulate_includes_the_sensitivity_grid_when_asked(client, dataset):
    response = client.post(
        "/api/simulate/",
        {"n_years": 500, "seed": 5, "include_sensitivity": True, "sensitivity_years": 200},
        format="json",
    )

    assert response.status_code == 200
    grid = response.json()["sensitivity"]
    assert len(grid["cells"]) == 9
    assert len(grid["aal_range"]) == 2
    assert grid["spread_factor"] >= 1.0
    assert grid["explanation"]


def test_simulate_curve_points_are_capped(client, dataset):
    response = client.post(
        "/api/simulate/",
        {"n_years": 500, "curve_points": 5_000, "include_sensitivity": False},
        format="json",
    )

    assert response.status_code == 400
    assert "curve_points" in response.json()


@pytest.mark.parametrize(
    "payload",
    [
        {"n_years": 1},
        {"n_years": 10_000_000},
        {"seed": -1},
        {"severity_threshold": "extreme"},
        {"session_window_hours": 0},
        {"session_window_hours": 100_000},
    ],
)
def test_simulate_rejects_out_of_range_requests(client, payload):
    response = client.post("/api/simulate/", payload, format="json")

    assert response.status_code == 400


# ---------------------------------------------------------------- the schema


def test_every_endpoint_appears_in_the_openapi_schema(client):
    response = client.get("/api/schema/")

    assert response.status_code == 200
    schema = response.content.decode()
    for path in (
        "/api/assets/",
        "/api/telemetry/summary/",
        "/api/frequency/",
        "/api/severity/",
        "/api/simulate/",
    ):
        assert path in schema


def test_the_docs_page_renders(client):
    assert client.get("/api/docs/").status_code == 200
