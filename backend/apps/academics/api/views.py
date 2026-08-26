from __future__ import annotations

from drf_spectacular.utils import extend_schema_view

from rest_framework import generics

from apps.academics.models import (
    Grade,
    Stream,
    TeachingGroup,
    Subject,
    LessonRequirement,
)

from .serializers import (
    GradeSerializer,
    StreamSerializer,
    TeachingGroupSerializer,
    SubjectSerializer,
    LessonRequirementSerializer,
)


@extend_schema_view()
class GradeListCreateView(generics.ListCreateAPIView):
    """
    List and create grades.
    """

    queryset = Grade.objects.select_related(
        "academic_year",
    ).all()
    serializer_class = GradeSerializer


class GradeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a grade.
    """

    queryset = Grade.objects.select_related(
        "academic_year",
    ).all()
    serializer_class = GradeSerializer


class StreamListCreateView(generics.ListCreateAPIView):
    """
    List and create streams.
    """

    queryset = Stream.objects.select_related(
        "grade",
        "grade__academic_year",
    ).all()
    serializer_class = StreamSerializer


class StreamDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a stream.
    """

    queryset = Stream.objects.select_related(
        "grade",
        "grade__academic_year",
    ).all()
    serializer_class = StreamSerializer


class TeachingGroupListCreateView(generics.ListCreateAPIView):
    """
    List and create teaching groups.
    """

    queryset = TeachingGroup.objects.select_related(
        "stream",
        "stream__grade",
        "stream__grade__academic_year",
    ).all()
    serializer_class = TeachingGroupSerializer


class TeachingGroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a teaching group.
    """

    queryset = TeachingGroup.objects.select_related(
        "stream",
        "stream__grade",
        "stream__grade__academic_year",
    ).all()
    serializer_class = TeachingGroupSerializer


class SubjectListCreateView(generics.ListCreateAPIView):
    """
    List and create subjects.
    """

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a subject.
    """

    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


class LessonRequirementListCreateView(generics.ListCreateAPIView):
    """
    List and create lesson requirements.
    """

    queryset = LessonRequirement.objects.select_related(
        "term",
        "term__academic_year",
        "instructional_group",
        "instructional_group__teaching_group__stream__grade",
        "subject",
    ).all()
    serializer_class = LessonRequirementSerializer


class LessonRequirementDetailView(
    generics.RetrieveUpdateDestroyAPIView,
):
    """
    Retrieve, update, or delete a lesson requirement.
    """

    queryset = LessonRequirement.objects.select_related(
        "term",
        "term__academic_year",
        "instructional_group",
        "instructional_group__teaching_group__stream__grade",
        "subject",
    ).all()
    serializer_class = LessonRequirementSerializer
