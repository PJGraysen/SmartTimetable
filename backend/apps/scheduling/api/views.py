from __future__ import annotations

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scheduling.engine.application.scheduling_application import (
    SchedulingApplicationService,
)
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
    TimetableEntry,
)

from .serializers import (
    SchedulingRunCreateSerializer,
    SchedulingRunExecuteSerializer,
    SchedulingRunResultSerializer,
    SchedulingRunSerializer,
)


class SchedulingRunListCreateView(APIView):
    """
    List and create scheduling runs.
    """

    def get(self, request):
        queryset = (
            SchedulingRun.objects
            .select_related(
                "term",
                "timetable_version",
            )
            .all()
        )

        serializer = SchedulingRunSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = SchedulingRunCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        scheduling_run = serializer.save()

        return Response(
            SchedulingRunSerializer(scheduling_run).data,
            status=status.HTTP_201_CREATED,
        )


class SchedulingRunDetailView(APIView):
    """
    Retrieve a single scheduling run.
    """

    def get(self, request, pk):
        scheduling_run = get_object_or_404(
            SchedulingRun.objects.select_related(
                "term",
                "timetable_version",
            ),
            pk=pk,
        )

        serializer = SchedulingRunSerializer(
            scheduling_run,
        )

        return Response(serializer.data)


class SchedulingRunExecuteView(APIView):
    """
    Execute timetable generation for a scheduling run.
    """

    def post(self, request, pk):
        scheduling_run = get_object_or_404(
            SchedulingRun.objects.select_related("term"),
            pk=pk,
        )

        serializer = SchedulingRunExecuteSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        if scheduling_run.status not in (
            SchedulingRunStatus.PENDING,
            SchedulingRunStatus.RUNNING,
        ):
            return Response(
                {
                    "detail": (
                        "Only PENDING or RUNNING scheduling runs "
                        "can be executed."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            result = SchedulingApplicationService().execute(
                scheduling_run=scheduling_run,
                version_name=serializer.validated_data[
                    "version_name"
                ],
                version_number=serializer.validated_data[
                    "version_number"
                ],
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        except Exception as exc:
            return Response(
                {
                    "detail": "Scheduling execution failed.",
                    "error": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            SchedulingRunResultSerializer(
                result.scheduling_run,
            ).data,
            status=status.HTTP_200_OK,
        )


class SchedulingRunResultView(APIView):
    """
    Return the complete current result of a scheduling run.

    When a timetable has been successfully generated, the response
    includes the timetable version and all generated timetable entries.
    """

    def get(self, request, pk):
        timetable_entries_queryset = (
            TimetableEntry.objects
            .select_related(
                "period",
                "teacher",
                "teaching_group",
                "lesson_requirement",
                "room",
            )
            .order_by(
                "day",
                "period__number",
            )
        )

        scheduling_run = get_object_or_404(
            SchedulingRun.objects
            .select_related(
                "term",
                "timetable_version",
                "timetable_version__term",
            )
            .prefetch_related(
                Prefetch(
                    "timetable_version__entries",
                    queryset=timetable_entries_queryset,
                )
            ),
            pk=pk,
        )

        serializer = SchedulingRunResultSerializer(
            scheduling_run,
        )

        return Response(serializer.data)