"""HTTP views.

Views stay thin on purpose: parse the request, call `risk_engine`, serialize the
result. No modeling decision, no arithmetic and no data cleaning belongs here —
all of it lives in the pure package so it can be re-run without a server.
"""

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from risk_engine import __version__


@extend_schema(
    summary="Liveness probe",
    description="Returns the API status and the version of the risk engine it wraps.",
    responses={200: dict},
)
@api_view(["GET"])
def health(request: Request) -> Response:
    """Report that the API is up and which engine version it serves."""
    del request
    return Response({"status": "ok", "engine_version": __version__})
