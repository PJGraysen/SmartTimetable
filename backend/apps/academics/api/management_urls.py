from rest_framework.routers import DefaultRouter

from .management_views import (
    ManagementRoomViewSet,
    ManagementSubjectViewSet,
    ManagementTeacherViewSet,
    ManagementTeachingGroupViewSet,
)

router = DefaultRouter()

router.register(
    "teaching-groups",
    ManagementTeachingGroupViewSet,
    basename="management-teaching-group",
)

router.register(
    "teachers",
    ManagementTeacherViewSet,
    basename="management-teacher",
)

router.register(
    "subjects",
    ManagementSubjectViewSet,
    basename="management-subject",
)

router.register(
    "rooms",
    ManagementRoomViewSet,
    basename="management-room",
)

urlpatterns = router.urls