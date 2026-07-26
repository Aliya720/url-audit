# PulseWatch URL Configuration
# TRD §4 — API Contract: all endpoints under /api/

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # API endpoints
    path("api/", include("checks.urls")),
    # OpenAPI schema + Swagger UI (TRD §1.1 — drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Prometheus metrics (TRD §1.1)
    path("", include("django_prometheus.urls")),
]
