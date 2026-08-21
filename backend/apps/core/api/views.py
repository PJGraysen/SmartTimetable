from __future__ import annotations

from rest_framework import generics

from apps.core.models import (
    AcademicYear,
    School,
    Term,
)

from .serializers import (
    AcademicYearSerializer,
    SchoolSerializer,
    TermSerializer,
)


class SchoolListCreateView(generics.ListCreateAPIView):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer


class SchoolDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer


class AcademicYearListCreateView(generics.ListCreateAPIView):
    queryset = AcademicYear.objects.select_related(
        "school",
    ).all()
    serializer_class = AcademicYearSerializer


class AcademicYearDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicYear.objects.select_related(
        "school",
    ).all()
    serializer_class = AcademicYearSerializer


class TermListCreateView(generics.ListCreateAPIView):
    queryset = Term.objects.select_related(
        "academic_year",
    ).all()
    serializer_class = TermSerializer


class TermDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Term.objects.select_related(
        "academic_year",
    ).all()
    serializer_class = TermSerializer
