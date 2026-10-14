from __future__ import annotations

from drf_spectacular.utils import extend_schema_view

from rest_framework import generics

from apps.academics.models import (
    Grade,
    InstructionalGroup,
    Stream,
    TeachingGroup,
    Subject,
    LessonRequirement,
)

from .serializers import (
    GradeSerializer,
    InstructionalGroupSerializer,
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


class InstructionalGroupListView(generics.ListAPIView):
    """List the canonical schedulable learner cohorts."""

    queryset = InstructionalGroup.objects.select_related(
        "teaching_group",
        "teaching_group__stream",
        "teaching_group__stream__grade",
    ).all()
    serializer_class = InstructionalGroupSerializer


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

    Supports optional filtering: ?term=<id or name>, ?active=1.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        term_param = self.request.query_params.get("term")
        if term_param:
            qs = qs.filter(term_id=term_param) if len(term_param) == 36 \
                else qs.filter(term__name__iexact=term_param)
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True)
        return qs

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
