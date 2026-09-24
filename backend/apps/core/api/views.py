from __future__ import annotations

from rest_framework import viewsets
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


from django.utils import timezone
from datetime import timedelta
from apps.core.models import SchoolEvent as _SchoolEvent
from apps.core.api.serializers import SchoolEventSerializer as _SES


class SchoolEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = _SES

    def get_queryset(self):
        qs = _SchoolEvent.objects.filter(is_active=True)
        d = self.request.query_params.get("date")
        if d:
            qs = qs.filter(date=d)
        frm = self.request.query_params.get("from")
        if frm:
            qs = qs.filter(date__gte=frm)
        to = self.request.query_params.get("to")
        if to:
            qs = qs.filter(date__lte=to)
        if not (d or frm or to):
            today = timezone.localdate()
            horizon = today + timedelta(days=30)
            qs = qs.filter(date__gte=today, date__lte=horizon)
        return qs.order_by("date", "start_time")
