from rest_framework import viewsets

from apps.academics.models import Subject, TeachingGroup
from apps.scheduling.models import Room
from apps.users.models import Teacher

from .management_serializers import (
    ManagementRoomSerializer,
    ManagementSubjectSerializer,
    ManagementTeacherSerializer,
    ManagementTeachingGroupSerializer,
)


class ManagementTeachingGroupViewSet(viewsets.ModelViewSet):
    queryset = (
        TeachingGroup.objects
        .select_related("stream", "stream__grade")
        .all()
        .order_by("stream__grade__name", "stream__name", "name")
    )
    serializer_class = ManagementTeachingGroupSerializer


class ManagementTeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all().order_by(
        "employee_code"
    )
    serializer_class = ManagementTeacherSerializer


class ManagementSubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by("code")
    serializer_class = ManagementSubjectSerializer


class ManagementRoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by("code")
    serializer_class = ManagementRoomSerializer