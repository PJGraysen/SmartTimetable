from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
"""
URL configuration for SmartTimetable Pro.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("api/library/", include("apps.library.urls")),
    path("api/platform/", include("apps.platform.urls")),
    path("api/ai/", include("apps.core.api.ai_urls")),
    path("api/audit/", include("apps.audit.urls")),

    path(
        "admin/",
        admin.site.urls,
    ),

    # API documentation
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
        ),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(
            url_name="schema",
        ),
        name="redoc",
    ),

    # Core API
    path(
        "api/core/",
        include("apps.core.api.urls"),
    ),

    # Scheduling API
    path(
        "api/scheduling/",
        include("apps.scheduling.api.urls"),
    ),

    # Inventory & Assets API
    path(
        "api/inventory/",
        include("apps.inventory.api.urls"),
    ),

    # Academics API
    path(
        "api/academics/",
        include("apps.academics.api.urls"),
    ),

    # Academics management API
    path(
        "api/academics/management/",
        include("apps.academics.api.management_urls"),
    ),
]


# ---- school event API (calendar) ----
from rest_framework.routers import DefaultRouter
from apps.core.api.views import SchoolEventViewSet

_events_router = DefaultRouter()
_events_router.register("api/core/events", SchoolEventViewSet, basename="school-event")
urlpatterns = urlpatterns + _events_router.urls


# ---- Serve uploaded media in dev ----
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# ------------------------------------------------------------------
# Notifications + approvals (SmartTimetable Pro)
# ------------------------------------------------------------------
from rest_framework.routers import DefaultRouter as _NotifRouter
from apps.core.notifications_api import (
    NotificationViewSet as _NVS, ApprovalRequestViewSet as _AVS,
)

_notif_router = _NotifRouter()
_notif_router.register("notifications", _NVS, basename="notification")
_notif_router.register("approvals", _AVS, basename="approval")

urlpatterns += [
    path("api/", include(_notif_router.urls)),
]
