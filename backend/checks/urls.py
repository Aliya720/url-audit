# checks app URL configuration

from django.urls import path

from . import views

urlpatterns = [
    # Check/Audit endpoints (Must-have — TRD §4.1, §4.2)
    path("audits", views.AuditCreateView.as_view(), name="audit-create"),
    path("audits/<str:audit_id>", views.AuditDetailView.as_view(), name="audit-detail"),
    # Health check (TRD §4.3)
    path("health", views.HealthCheckView.as_view(), name="health-check"),
    # Monitor endpoints (Should-have — TRD §4.4–§4.7)
    path("monitors", views.MonitorListCreateView.as_view(), name="monitor-list-create"),
    path("monitors/alerts", views.MonitorAlertsView.as_view(), name="monitor-alerts"),
    path(
        "monitors/<str:monitor_id>",
        views.MonitorDetailView.as_view(),
        name="monitor-detail",
    ),
    path(
        "monitors/<str:monitor_id>/history",
        views.MonitorHistoryView.as_view(),
        name="monitor-history",
    ),
]
