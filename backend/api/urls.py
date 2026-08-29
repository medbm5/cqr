"""URL routing for the presentation API."""

from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from api import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", views.health, name="health"),
    path("api/assets/", views.assets, name="assets"),
    path("api/telemetry/summary/", views.telemetry_summary, name="telemetry-summary"),
    path("api/frequency/", views.frequency, name="frequency"),
    path("api/severity/", views.severity, name="severity"),
    path("api/simulate/", views.simulate, name="simulate"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
