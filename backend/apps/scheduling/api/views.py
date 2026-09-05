from __future__ import annotations

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

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

from .pagination import SchedulingRunPagination

from .serializers import (
    SchedulingRunCreateSerializer,
    SchedulingRunExecuteSerializer,
    SchedulingRunResultSerializer,
    SchedulingRunSerializer,
)


@extend_schema_view(
    get=extend_schema(
        operation_id="scheduling_runs_list",
        summary="List scheduling runs",
        description=(
            "Return all scheduling runs with their current "
            "execution and solver status."
        ),
        responses=SchedulingRunSerializer(many=True),
    ),
    post=extend_schema(
        operation_id="scheduling_runs_create",
        summary="Create a scheduling run",
        description=(
            "Create a new pending scheduling run for an "
            "academic term."
        ),
        request=SchedulingRunCreateSerializer,
        responses={
            201: SchedulingRunSerializer,
        },
    ),
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
            SchedulingRunSerializer(
                scheduling_run,
            ).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="scheduling_runs_retrieve",
        summary="Retrieve a scheduling run",
        description=(
            "Return the current state and execution information "
            "for a single scheduling run."
        ),
        responses=SchedulingRunSerializer,
    ),
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


@extend_schema_view(
    post=extend_schema(
        operation_id="scheduling_runs_execute",
        summary="Execute a scheduling run",
        description=(
            "Execute timetable generation for a pending or "
            "running scheduling run."
        ),
        request=SchedulingRunExecuteSerializer,
        responses={
            200: SchedulingRunResultSerializer,
            409: OpenApiResponse(
                description=(
                    "The scheduling run cannot be executed "
                    "in its current state or the scheduling "
                    "request is invalid."
                ),
            ),
            500: OpenApiResponse(
                description="Scheduling execution failed.",
            ),
        },
    ),
)
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
            from django.utils import timezone

            scheduling_run.status = SchedulingRunStatus.FAILED
            scheduling_run.completed_at = timezone.now()
            scheduling_run.error_message = str(exc)

            scheduling_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "error_message",
                    "updated_at",
                ]
            )

            return Response(
                {
                    "detail": "Scheduling execution failed.",
                    "error": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            SchedulingRunSerializer(
                result.scheduling_run,
            ).data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        operation_id="scheduling_runs_results",
        summary="Retrieve scheduling run results",
        description=(
            "Return the complete current result of a scheduling run.\n\n"
            "When a timetable has been successfully generated, "
            "the response includes the timetable version and all "
            "generated timetable entries."
        ),
        responses=SchedulingRunResultSerializer,
    ),
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
                "instructional_group",
                "lesson_requirement",
                "lesson_requirement__subject",
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

