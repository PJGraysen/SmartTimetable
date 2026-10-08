from rest_framework.routers import DefaultRouter

from apps.audit.views import (
    AuditLogViewSet, ErrorRecordViewSet,
    HeartbeatView, ActiveUsersView,
)
from django.urls import path

router = DefaultRouter()
router.register("logs", AuditLogViewSet, basename="audit-log")
router.register("errors", ErrorRecordViewSet, basename="error-record")

urlpatterns = router.urls


urlpatterns += [
    path("heartbeat/", HeartbeatView.as_view(), name="audit-heartbeat"),
    path("active-users/", ActiveUsersView.as_view(), name="audit-active-users"),
]
