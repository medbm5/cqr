"""HTTP views.

Views stay thin on purpose: parse the request, call `risk_engine` through the
cached accessors in `pipeline`, serialize the result. No modeling decision, no
arithmetic and no data cleaning belongs here - all of it lives in the pure
package so it can be re-run without a server.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from risk_engine import __version__
from risk_engine.ingestion import SeverityClass

from . import pipeline
from .serializers import (
    AssetInventorySerializer,
    FrequencyResponseSerializer,
    SeverityResponseSerializer,
    SimulationRequestSerializer,
    SimulationResponseSerializer,
    TelemetryResponseSerializer,
)

FREQUENCY_PARAMETERS = [
    OpenApiParameter(
        "severity_threshold",
        OpenApiTypes.STR,
        enum=[member.value for member in SeverityClass],
        description="Minimum severity for an event to count as an attack. Default: high.",
    ),
    OpenApiParameter(
        "session_window_hours",
        OpenApiTypes.NUMBER,
        description="Quiet period that ends an episode. Default: 24.",
    ),
]


def _frequency_from(request: Request) -> Any:
    """Read the two frequency conventions off the query string.

    Raises:
        ValueError: If either parameter is present but unusable, which the view
            turns into a 400.
    """
    raw_threshold = request.query_params.get("severity_threshold", pipeline.DEFAULT_THRESHOLD.value)
    try:
        threshold = SeverityClass(raw_threshold)
    except ValueError:
        raise ValueError(
            f"severity_threshold must be one of "
            f"{[member.value for member in SeverityClass]}, got {raw_threshold!r}"
        ) from None

    raw_window = request.query_params.get(
        "session_window_hours", str(pipeline.DEFAULT_WINDOW_HOURS)
    )
    try:
        window = float(raw_window)
    except (TypeError, ValueError):
        raise ValueError(f"session_window_hours must be a number, got {raw_window!r}") from None
    if window <= 0:
        raise ValueError(f"session_window_hours must be positive, got {window}")

    return pipeline.get_frequency(threshold, window)


@extend_schema(
    summary="Liveness probe",
    description="Returns the API status and the version of the risk engine it wraps.",
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
def health(request: Request) -> Response:
    """Report that the API is up and which engine version it serves."""
    del request
    return Response({"status": "ok", "engine_version": __version__})


@extend_schema(
    summary="Asset inventory with attack activity",
    description=(
        "The estate from the asset reference, joined to the episodes attributed to each "
        "machine, plus the same counts grouped by criticality and environment."
    ),
    parameters=FREQUENCY_PARAMETERS,
    responses={200: AssetInventorySerializer},
)
@api_view(["GET"])
def assets(request: Request) -> Response:
    """List the estate with per-asset episode counts."""
    try:
        frequency = _frequency_from(request)
    except ValueError as error:
        return Response({"detail": str(error)}, status=400)

    return Response(AssetInventorySerializer(frequency).data)


@extend_schema(
    summary="Telemetry normalization and shape",
    description=(
        "The normalization report accounting for every row from the two feeds, with weekly "
        "event counts split by which feed saw them, the severity mix and the technique mix."
    ),
    responses={200: TelemetryResponseSerializer},
)
@api_view(["GET"])
def telemetry_summary(request: Request) -> Response:
    """Report what ingestion did and what the telemetry looks like."""
    del request
    dataset = pipeline.get_dataset()
    return Response(
        TelemetryResponseSerializer(
            {"normalization": dataset.ingestion.report, "summary": dataset.telemetry}
        ).data
    )


@extend_schema(
    summary="Annualized attack frequency",
    description=(
        "Attack rates per year, segmented by attack type, with the conventions used echoed "
        "back and the numbered trace from raw rows through to lambda."
    ),
    parameters=FREQUENCY_PARAMETERS,
    responses={200: FrequencyResponseSerializer},
)
@api_view(["GET"])
def frequency(request: Request) -> Response:
    """Estimate attack frequency under the requested conventions."""
    try:
        estimate = _frequency_from(request)
    except ValueError as error:
        return Response({"detail": str(error)}, status=400)

    return Response(FrequencyResponseSerializer(estimate).data)


@extend_schema(
    summary="Loss severity per attack type",
    description=(
        "Fitted lognormal parameters per attack type with their peer-weighted sample sizes, "
        "the diagnostics challenging each fit, and histogram plus fitted-curve data for a chart."
    ),
    responses={200: SeverityResponseSerializer},
)
@api_view(["GET"])
def severity(request: Request) -> Response:
    """Return the fitted severity model and its diagnostics."""
    del request
    return Response(SeverityResponseSerializer(pipeline.get_dataset().severity).data)


@extend_schema(
    summary="Simulate annual loss",
    description=(
        "Compound frequency and severity into a distribution of annual loss, returning AAL, "
        "VaR and TVaR, both exceedance curves, the parameter sweep and the full explanation "
        "chain. Repeated requests with identical arguments are served from cache."
    ),
    request=SimulationRequestSerializer,
    responses={200: SimulationResponseSerializer},
)
@api_view(["POST"])
def simulate(request: Request) -> Response:
    """Run the Monte Carlo simulation for the requested parameters."""
    form = SimulationRequestSerializer(data=request.data)
    form.is_valid(raise_exception=True)
    options = form.validated_data

    result = pipeline.get_simulation(
        options["n_years"],
        options["seed"],
        SeverityClass(options["severity_threshold"]),
        options["session_window_hours"],
    )
    grid = (
        pipeline.get_sensitivity(options["seed"], options["sensitivity_years"])
        if options["include_sensitivity"]
        else None
    )
    return Response(SimulationResponseSerializer(_payload(result, grid, options)).data)


def _payload(result: Any, grid: Any, options: dict[str, Any]) -> dict[str, Any]:
    """Assemble the simulation response from engine objects.

    Shaping only: every value here is read off the result, none is computed.
    """
    points = options["curve_points"]
    return {
        "metrics": result.metrics,
        "aep_curve": result.curve("aep", points=points),
        "oep_curve": result.curve("oep", points=points),
        "histogram": result.histogram(bins=options["histogram_bins"]),
        "expected_loss_by_attack_type": {
            attack_type.value: value for attack_type, value in result.expected_loss_by_type.items()
        },
        "expected_incidents_by_attack_type": {
            attack_type.value: value
            for attack_type, value in result.expected_incidents_by_type.items()
        },
        "n_years": result.params.n_years,
        "seed": result.params.seed,
        "params": result.frequency.params,
        "sensitivity": grid,
        "explanation": result.to_explanation(),
    }
