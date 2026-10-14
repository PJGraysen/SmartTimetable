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

import logging

from django.utils import timezone

from apps.audit.models import (
    AuditAction,
    AuditLog,
    ErrorRecord,
    ErrorSeverity,
    ErrorStatus,
)
from apps.scheduling.engine.solver.outcomes import (
    FailureReport,
    describe_failure,
)
from apps.scheduling.models import SchedulingErrorLog

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

    logger = logging.getLogger(__name__)

    def post(self, request, pk):
        scheduling_run = get_object_or_404(
            SchedulingRun.objects.select_related("term"),
            pk=pk,
        )

        serializer = SchedulingRunExecuteSerializer(data=request.data)
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
                version_name=serializer.validated_data["version_name"],
                version_number=serializer.validated_data["version_number"],
            )
        except ValueError as exc:
            return self._respond_to_failure(
                request=request,
                scheduling_run=scheduling_run,
                failure=FailureReport(
                    code="CONTRACT_VIOLATION",
                    user_message=(
                        "The scheduling contract is invalid and "
                        "generation cannot proceed. Contact the "
                        "timetabling administrator."
                    ),
                    technical_detail=str(exc),
                    hints=(
                        "Review the latest block / stream / quota changes.",
                    ),
                ),
                http_status=status.HTTP_409_CONFLICT,
            )
        except Exception as exc:
            self.logger.exception(
                "Timetable generation raised unexpectedly",
                extra={
                    "scheduling_run_id": str(scheduling_run.pk),
                    "user_id": getattr(request.user, "pk", None),
                },
            )
            if self._looks_like_persistence_failure(exc):
                failure = FailureReport(
                    code="PERSISTENCE_FAILURE",
                    user_message=(
                        "The timetable was generated successfully, but "
                        "it could not be saved. The administrator has "
                        "been notified and will resolve the storage "
                        "issue."
                    ),
                    technical_detail=str(exc),
                    hints=(
                        "This is a storage or configuration issue, not "
                        "a scheduling-rules conflict.",
                        "The solver succeeded; retrying after the "
                        "underlying issue is fixed should reproduce the "
                        "same timetable.",
                    ),
                )
            else:
                failure = FailureReport(
                    code="SOLVER_FAILURE",
                    user_message=(
                        "Timetable generation failed unexpectedly. "
                        "The administrator has been notified."
                    ),
                    technical_detail=str(exc),
                )
            return self._respond_to_failure(
                request=request,
                scheduling_run=scheduling_run,
                failure=failure,
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        run = result.scheduling_run
        if not self._run_succeeded(run):
            solver_result = getattr(result, "solver_result", None)
            if solver_result is not None:
                failure = describe_failure(
                    solver_result,
                    unsat_core_names=getattr(
                        solver_result, "unsat_core_names", ()
                    ),
                )
            else:
                failure = FailureReport(
                    code="SOLVER_FAILURE",
                    user_message=(
                        "Timetable generation did not produce a "
                        "usable schedule."
                    ),
                    technical_detail=(
                        getattr(run, "error_message", "") or ""
                    ),
                )
            return self._respond_to_failure(
                request=request,
                scheduling_run=run,
                failure=failure,
                http_status=status.HTTP_409_CONFLICT,
            )

        return Response(
            SchedulingRunSerializer(run).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # Failure plumbing
    # ------------------------------------------------------------------

    @staticmethod
    def _run_succeeded(run) -> bool:
        solver_status = getattr(run, "solver_status", None)
        if solver_status is None:
            return getattr(run, "status", None) != SchedulingRunStatus.FAILED
        return str(solver_status).upper() in {"FEASIBLE", "OPTIMAL"}

    @staticmethod
    def _client_ip(request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR") or None

    @staticmethod
    def _looks_like_persistence_failure(exc: BaseException) -> bool:
        """
        Distinguish a storage-layer failure (solver succeeded, save
        failed) from a solver failure.

        Walks the exception traceback: if any frame originates from a
        module whose path contains ``persistence``, the failure is a
        persistence-layer failure. Also checks the exception type's
        module name as a fallback for wrapped or re-raised exceptions.
        This keeps the user-facing message accurate without coupling
        the view to specific exception types.
        """
        tb = getattr(exc, "__traceback__", None)
        while tb is not None:
            filename = (
                tb.tb_frame.f_code.co_filename
                .replace("\\", "/")
                .lower()
            )
            if "persistence" in filename:
                return True
            tb = tb.tb_next

        module_name = type(exc).__module__.lower()
        if "persistence" in module_name:
            return True

        return False

    def _respond_to_failure(
        self,
        *,
        request,
        scheduling_run,
        failure: FailureReport,
        http_status: int,
    ):
        user = request.user if request.user.is_authenticated else None

        self.logger.error(
            "Timetable generation failed: code=%s run=%s user=%s",
            failure.code,
            scheduling_run.pk,
            getattr(user, "pk", None),
            extra={
                "failure_code": failure.code,
                "scheduling_run_id": str(scheduling_run.pk),
                "technical_detail": failure.technical_detail,
            },
        )

        scheduling_run.status = SchedulingRunStatus.FAILED
        scheduling_run.completed_at = timezone.now()
        scheduling_run.error_message = (
            failure.technical_detail or failure.user_message
        )
        scheduling_run.save(
            update_fields=[
                "status",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )

        SchedulingErrorLog.objects.create(
            source="scheduling",
            severity="ERROR",
            code=failure.code,
            message=failure.user_message,
            context={
                "technical_detail": failure.technical_detail,
                "hints": list(failure.hints),
            },
            user=user,
            url=request.path,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:300],
            scheduling_run=scheduling_run,
        )

        ErrorRecord.objects.create(
            severity=ErrorSeverity.ERROR,
            status=ErrorStatus.OPEN,
            subsystem="scheduling",
            operation="timetable_generation",
            error_code=failure.code,
            message=failure.user_message,
            technical_exception=failure.technical_detail,
            entity_type="SchedulingRun",
            entity_id=str(scheduling_run.pk),
            solver_run_id=str(scheduling_run.pk),
            details={"hints": list(failure.hints)},
            user=user,
        )

        if user is not None:
            AuditLog.objects.create(
                user=user,
                action=AuditAction.GENERATE,
                entity_type="SchedulingRun",
                entity_id=str(scheduling_run.pk),
                description=(
                    f"Timetable generation failed ({failure.code}). "
                    f"{failure.user_message}"
                ),
                ip_address=self._client_ip(request),
            )

        return Response(
            {"error": failure.to_payload()},
            status=http_status,
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




# ---------------------------------------------------------------------
# Dashboard + approval actions (added 2026-09-20)
# ---------------------------------------------------------------------
from rest_framework.views import APIView as _APIView
from rest_framework.response import Response as _Response
from rest_framework.permissions import BasePermission as _BasePerm
from django.utils import timezone as _tz
from django.contrib.auth.models import User as _User
from apps.scheduling.models import (
    SchedulingRun as _SR,
    TimetableVersion as _TV,
    TimetableEntry as _TE,
    Period as _Period,
    SchedulingRunStatus as _SRS,
)
from apps.academics.models import TeachingGroup as _TG


class _IsAdmin(_BasePerm):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


class SchedulingDashboardView(_APIView):
    """Single-call payload for the Scheduling page header + history."""
    permission_classes = [_IsAdmin]

    def get(self, request):
        from apps.core.models import Term

        # Terms
        all_terms = list(
            Term.objects.all()
            .select_related("academic_year")
            .order_by("academic_year__name", "name")
        )
        terms_payload = [
            {
                "id": str(t.id),
                "name": t.name,
                "academic_year_name": t.academic_year.name,
                "is_active": t.is_active,
            }
            for t in all_terms
        ]
        active_term = next((t for t in terms_payload if t["is_active"]), None)

        # Header version: newest for the currently active term.
        # Falls back to the newest is_active version when no active
        # term is set. This keeps the header aligned with the LIVE
        # banner and the fingerprint (both read the newest version)
        # instead of stalling on the last approved one.
        if active_term:
            active_version = (
                _TV.objects
                .filter(term_id=active_term["id"])
                .order_by("-created_at")
                .first()
            )
        else:
            active_version = (
                _TV.objects
                .filter(is_active=True)
                .order_by("-created_at")
                .first()
            )
        active_payload = None
        days_count = 0
        classes_count = 0
        entries_count = 0
        if active_version:
            entries_count = _TE.objects.filter(timetable_version=active_version).count()
            days_count = (
                _TE.objects.filter(timetable_version=active_version)
                .values("day").distinct().count()
            )
            classes_count = (
                _TE.objects.filter(timetable_version=active_version)
                .values("instructional_group__teaching_group_id")
                .distinct().count()
            )
            active_payload = {
                "id": str(active_version.id),
                "name": active_version.name,
                "version_number": active_version.version_number,
                "created_at": active_version.created_at.isoformat(),
                "is_published": active_version.is_published,
                "entries_count": entries_count,
                "days": days_count,
                "classes": classes_count,
            }

        # Last successful sync = last completed run with an approved version
        last_completed = _SR.objects.filter(
            status=_SRS.COMPLETED,
        ).order_by("-completed_at").first()
        last_successful_sync = (
            last_completed.completed_at.isoformat()
            if last_completed and last_completed.completed_at else None
        )

        # Recent runs: last 5 COMPLETED (approved or not). Each row
        # carries its own approved_at flag; approving one must not
        # hide the others from the list.
        recent_runs_qs = list(
            _SR.objects.filter(status=_SRS.COMPLETED)
            .select_related("term", "term__academic_year", "timetable_version", "approved_by")
            .order_by("-completed_at", "-created_at")[:5]
        )

        def _run_row(r):
            return {
                "id": str(r.id),
                "status": r.status,
                "status_display": r.get_status_display(),
                "term_name": f"{r.term.academic_year.name} / {r.term.name}",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "approved_at": r.approved_at.isoformat() if r.approved_at else None,
                "approved_by": (
                    r.approved_by.get_full_name() or r.approved_by.username
                    if r.approved_by else None
                ),
                "version_name": r.timetable_version.name if r.timetable_version else None,
                "version_number": (
                    r.timetable_version.version_number if r.timetable_version else None
                ),
                "error_message": r.error_message or "",
            }

        recent_runs = [_run_row(r) for r in recent_runs_qs]

        # Failed runs
        failed_runs = [
            _run_row(r)
            for r in _SR.objects.filter(status=_SRS.FAILED)
            .select_related("term", "term__academic_year")
            .order_by("-created_at")[:5]
        ]

        # Counts
        counts = {
            "total": _SR.objects.count(),
            "completed": _SR.objects.filter(status=_SRS.COMPLETED).count(),
            "failed": _SR.objects.filter(status=_SRS.FAILED).count(),
            "cancelled": _SR.objects.filter(status=_SRS.CANCELLED).count(),
            "approved": _SR.objects.filter(approved_at__isnull=False).count(),
        }

        return _Response({
            "active_term": active_term,
            "terms": terms_payload,
            "active_version": active_payload,
            "last_successful_sync": last_successful_sync,
            "recent_runs": recent_runs,
            "failed_runs": failed_runs,
            "counts": counts,
        })


class SchedulingRunApproveView(_APIView):
    permission_classes = [_IsAdmin]

    def post(self, request, pk):
        try:
            run = _SR.objects.get(id=pk)
        except _SR.DoesNotExist:
            return _Response({"detail": "not found"}, status=404)
        if run.status != _SRS.COMPLETED:
            return _Response(
                {"detail": "Only completed runs can be approved."},
                status=400,
            )

        # Block approval when unresolved hard constraints exist
        from apps.scheduling.models import (
            ValidationResult as _VRG,
            ValidationSeverity as _VSG,
        )
        unresolved = _VRG.objects.filter(
            scheduling_run=run,
            severity=_VSG.ERROR,
            is_resolved=False,
        ).count()
        if unresolved > 0:
            return _Response(
                {
                    "detail": (
                        f"Cannot approve: {unresolved} unresolved hard-constraint "
                        "violation(s). Open the constraint report and fix them first."
                    ),
                    "unresolved_hard_constraints": unresolved,
                },
                status=400,
            )
        note = (request.data.get("note") or "").strip()
        run.approved_at = _tz.now()
        run.approved_by = request.user
        run.approval_note = note
        run.save(update_fields=["approved_at", "approved_by", "approval_note", "updated_at"])

        # Publish the linked timetable version, deactivate others for the same term
        if run.timetable_version:
            _TV.objects.filter(term=run.term).exclude(id=run.timetable_version_id).update(
                is_active=False
            )
            _TV.objects.filter(id=run.timetable_version_id).update(
                is_active=True, is_published=True
            )

        # Audit
        try:
            from apps.academics.audit_util import log_event
            log_event(
                request,
                action="PUBLISH",
                entity_type="SchedulingRun",
                entity_label=f"Approved run {str(run.id)[:8]} ({run.timetable_version.name if run.timetable_version else 'no version'})",
                entity_id=run.id,
                meta={"note": note},
            )
        except Exception:
            pass

        return _Response({"ok": True, "run_id": str(run.id)})


class SchedulingRunUnapproveView(_APIView):
    permission_classes = [_IsAdmin]

    def post(self, request, pk):
        try:
            run = _SR.objects.get(id=pk)
        except _SR.DoesNotExist:
            return _Response({"detail": "not found"}, status=404)
        run.approved_at = None
        run.approved_by = None
        run.approval_note = ""
        run.save(update_fields=["approved_at", "approved_by", "approval_note", "updated_at"])
        return _Response({"ok": True})



# ---------------------------------------------------------------------
# Constraint report + error logging (added 2026-09-20)
# ---------------------------------------------------------------------
from apps.scheduling.models import (
    ValidationResult as _VR,
    ValidationSeverity as _VS,
    ValidationCategory as _VC,
    SchedulingErrorLog as _SEL,
)
from rest_framework.views import APIView as _APIView2
from rest_framework.response import Response as _Resp2
from rest_framework.permissions import BasePermission as _BP2


class SchedulingRunDiscardView(_APIView):
    """
    Discard a completed but unapproved scheduling run.

    Marks the run CANCELLED so it disappears from the recent-successful-runs
    list without deleting the audit trail.
    """
    permission_classes = [_IsAdmin]

    def post(self, request, pk):
        run = get_object_or_404(_SR, pk=pk)
        if run.approved_at is not None:
            return _Response(
                {"detail": "Cannot discard an approved run. Unapprove first."},
                status=409,
            )
        run.status = _SRS.CANCELLED
        run.save(update_fields=["status", "updated_at"])
        return _Response({"ok": True})


class _IsAdmin2(_BP2):
    def has_permission(self, request, view):
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


class _AnyAuthenticated(_BP2):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


# Mitigation advice keyed by validation category
_MITIGATION = {
    "TEACHER_CLASH":
        "Two lessons were assigned to the same teacher in one period. "
        "Allow another qualified teacher for the requirement, or reduce lessons per week.",
    "GROUP_CLASH":
        "A class was scheduled in two lessons in one period. "
        "Review parallel-block configuration or reduce lessons/week for the affected subject.",
    "ROOM_CLASH":
        "The same room was booked twice in one period. "
        "Add another room with sufficient capacity, or allow the lesson to run without a fixed room.",
    "TEACHER_UNAVAILABLE":
        "A teacher was scheduled during an unavailable slot. "
        "Update TeacherAvailability for the affected term, day or period.",
    "ROOM_UNAVAILABLE":
        "A room was scheduled during an unavailable slot. "
        "Update RoomAvailability for the affected term, day or period.",
    "FREE_AFTERNOON_VIOLATION":
        "A teacher was scheduled on their mandatory free afternoon. "
        "Reassign the lesson, or change TeacherFreeAfternoon for the affected term.",
    "MISSING_TEACHER_ASSIGNMENT":
        "A lesson has no eligible teacher. "
        "Add a teacher in Academics → Lesson Requirements before re-running.",
    "INVALID_LESSON_REQUIREMENT":
        "A lesson requirement is malformed (missing group/subject, or lessons_per_week = 0). "
        "Fix it in Academics → Lesson Requirements.",
    "INVALID_PERIOD":
        "A period is misconfigured. Review Periods (morning/afternoon classification, times).",
    "INVALID_TIMETABLE_ENTRY":
        "A scheduled entry is malformed. Re-run generation.",
    "UNSCHEDULED_LESSON":
        "One or more lesson requirements could not be placed. "
        "Free a slot, reduce lessons/week, add a teacher, or add a room.",
    "CONSTRAINT_VIOLATION":
        "A hard constraint was violated. Review the solver diagnostics for details.",
    "CONFIGURATION_ERROR":
        "The scheduler is misconfigured. Check engine settings and re-run.",
    "OTHER":
        "Review the validation result details.",
}


def _mitigation_for(category: str) -> str:
    return _MITIGATION.get(category, _MITIGATION["OTHER"])


class SchedulingRunReportView(_APIView2):
    """Constraint satisfaction report for one run."""
    permission_classes = [_IsAdmin2]

    def get(self, request, pk):
        try:
            run = _SR.objects.get(id=pk)
        except _SR.DoesNotExist:
            return _Resp2({"detail": "not found"}, status=404)

        findings = _VR.objects.filter(scheduling_run=run).order_by("severity", "category")

        def _bucket(sev):
            return [
                {
                    "id": str(f.id),
                    "category": f.category,
                    "category_display": f.get_category_display(),
                    "message": f.message,
                    "mitigation": _mitigation_for(f.category),
                    "details": f.details or {},
                    "is_resolved": f.is_resolved,
                }
                for f in findings if f.severity == sev
            ]

        hard = _bucket(_VS.ERROR)
        soft = _bucket(_VS.WARNING)
        info = _bucket(_VS.INFO)

        # Resolved counts (a run can have entries marked resolved after manual fixes)
        unresolved_hard = [f for f in hard if not f["is_resolved"]]

        approvable = (
            run.status == "COMPLETED"
            and len(unresolved_hard) == 0
        )

        reason_if_blocked = None
        if run.status != "COMPLETED":
            reason_if_blocked = f"Run status is {run.status}; only COMPLETED runs can be approved."
        elif unresolved_hard:
            reason_if_blocked = (
                f"{len(unresolved_hard)} hard-constraint violation(s) must be resolved before approval."
            )

        return _Resp2({
            "run_id": str(run.id),
            "status": run.status,
            "solver_status": run.solver_status,
            "approvable": approvable,
            "reason_if_blocked": reason_if_blocked,
            "hard_constraints": hard,
            "soft_constraints": soft,
            "info": info,
            "counts": {
                "hard": len(hard),
                "hard_unresolved": len(unresolved_hard),
                "soft": len(soft),
                "info": len(info),
            },
        })


class SchedulingErrorReportView(_APIView2):
    """Frontend reports an error → stored for admin review."""
    permission_classes = [_AnyAuthenticated]

    def post(self, request):
        data = request.data or {}
        source = (data.get("source") or "scheduling")[:50]
        severity = data.get("severity") or "ERROR"
        if severity not in ("ERROR", "WARNING", "INFO"):
            severity = "ERROR"
        message = (data.get("message") or "").strip()
        if not message:
            return _Resp2({"detail": "message required"}, status=400)

        log = _SEL.objects.create(
            source=source,
            severity=severity,
            code=(data.get("code") or "")[:80],
            message=message[:4000],
            context=data.get("context") or {},
            user=request.user if request.user.is_authenticated else None,
            url=(data.get("url") or "")[:500],
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:300],
            scheduling_run_id=data.get("scheduling_run") or None,
        )
        return _Resp2({"ok": True, "id": str(log.id)}, status=201)


class SchedulingErrorListView(_APIView2):
    """Admin console: recent error logs."""
    permission_classes = [_IsAdmin2]

    def get(self, request):
        qs = _SEL.objects.select_related("user").order_by("-created_at")
        severity = request.query_params.get("severity")
        source = request.query_params.get("source")
        if severity:
            qs = qs.filter(severity=severity)
        if source:
            qs = qs.filter(source=source)

        rows = [
            {
                "id": str(x.id),
                "created_at": x.created_at.isoformat(),
                "source": x.source,
                "severity": x.severity,
                "code": x.code,
                "message": x.message,
                "context": x.context,
                "user": (
                    x.user.get_full_name() or x.user.username
                    if x.user else None
                ),
                "url": x.url,
            }
            for x in qs[:200]
        ]
        return _Resp2({"count": len(rows), "results": rows})


class SchedulingResolveValidationView(_APIView2):
    """Mark or unmark a validation finding as resolved."""
    permission_classes = [_IsAdmin2]

    def post(self, request, run_id, validation_id):
        try:
            v = _VR.objects.get(id=validation_id, scheduling_run_id=run_id)
        except _VR.DoesNotExist:
            return _Resp2({"detail": "not found"}, status=404)
        resolved = bool(request.data.get("resolved", True))
        v.is_resolved = resolved
        v.save(update_fields=["is_resolved", "updated_at"])
        # Optional: notify via audit log
        try:
            from apps.academics.audit_util import log_event
            log_event(
                request,
                action="UPDATE",
                entity_type="ValidationResult",
                entity_label=f"{v.category} → {'resolved' if resolved else 'reopened'}",
                entity_id=v.id,
            )
        except Exception:
            pass
        return _Resp2({"ok": True, "id": str(v.id), "is_resolved": v.is_resolved})
