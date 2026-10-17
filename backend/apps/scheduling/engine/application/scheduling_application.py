from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.scheduling.engine.application.scheduler import (
    create_default_scheduler,
)
from apps.scheduling.engine.infrastructure.django_loader import (
    DjangoSchedulingLoader,
)
from apps.scheduling.engine.application.timetable_persistence import (
    PersistenceResult,
    TimetablePersistenceService,
)
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
)


def load_scheduling_problem(*, term, hint_assignments=()):
    """
    Compatibility boundary for the application-layer scheduling loader.

    hint_assignments, when provided, is a tuple of
    (lesson_requirement_id, day, period_id) that seeds the solver with
    the current live version's layout. Hints are soft — they bias the
    search, not constrain it. Master scope passes () and behavior is
    identical to a plain unscoped run.
    """
    loader = DjangoSchedulingLoader()
    problem = loader.load_problem(term=term)
    if hint_assignments:
        from dataclasses import replace as _replace
        problem = _replace(problem, hint_assignments=hint_assignments)
    return problem


def compute_hints_for_scope(*, term, scope_kind, scope_id, baseline_version_id=None):
    """
    Return hint assignments for the current term.

    Master scope (or no scope) returns () so the solver is fully free.

    Scoped runs return hints for OUT-OF-SCOPE entries only. In-scope
    entries are omitted so the solver is free to re-arrange them.
    Out-of-scope entries are hinted at their current
    (lesson_requirement, day, period) so the solver is biased to leave
    them where they are. Net effect: anchored outside the scope, free
    inside it.

    Unknown scope_kind/scope_id returns () -- an unconstrained run is
    preferable to a run that pretends to scope but does not.
    """
    if not scope_kind or scope_kind == "master":
        return ()
    if not scope_id:
        return ()

    from apps.scheduling.models import (
        TimetableEntry, TimetableVersion, InstructionalGroup,
    )

    kind = str(scope_kind).strip().lower()
    sid = str(scope_id).strip().upper()

    in_scope_group_ids = None
    in_scope_subject_codes = None

    if kind == "grade":
        wanted = {sid + "E", sid + "W"}
        in_scope_group_ids = set(
            InstructionalGroup.objects
            .filter(is_active=True, code__in=wanted)
            .values_list("id", flat=True)
        )
    elif kind == "subject":
        in_scope_subject_codes = {sid}
    else:
        return ()

    if baseline_version_id:
        v = TimetableVersion.objects.filter(
            term=term, id=baseline_version_id,
        ).first()
    else:
        v = (
            TimetableVersion.objects
            .filter(term=term, is_active=True)
            .order_by("-created_at")
            .first()
        )
    if v is None:
        return ()

    hints = []
    qs = (
        TimetableEntry.objects
        .filter(timetable_version=v)
        .select_related("lesson_requirement")
    )
    for e in qs:
        if e.lesson_requirement_id is None:
            continue

        is_in_scope = False
        if in_scope_group_ids is not None:
            if e.instructional_group_id in in_scope_group_ids:
                is_in_scope = True
        elif in_scope_subject_codes is not None:
            lr = e.lesson_requirement
            subj = (
                getattr(lr, "subject_code", None)
                or getattr(getattr(lr, "subject", None), "code", None)
            )
            if subj and str(subj).strip().upper() in in_scope_subject_codes:
                is_in_scope = True

        if not is_in_scope:
            hints.append((e.lesson_requirement_id, e.day, e.period_id))

    return tuple(hints)


class SchedulingExecutionResult:
    """Result returned by the scheduling application service."""

    def __init__(self, scheduling_run, solver_result=None, persistence_result=None):
        self.scheduling_run = scheduling_run
        self.solver_result = solver_result
        self.persistence_result = persistence_result


class SchedulingApplicationService:
    """
    Application-layer orchestration for timetable generation.

    The application service coordinates:
        SchedulingRun state
        Django -> domain loading
        scheduler execution
        timetable persistence

    Historical scheduling records are preserved.
    """

    def __init__(
        self,
        scheduler=None,
        persistence=None,
        loader=None,
    ):
        self.scheduler = scheduler or create_default_scheduler()
        self.persistence = persistence or TimetablePersistenceService()
        self.loader = loader or DjangoSchedulingLoader()

    def execute(
        self,
        scheduling_run: SchedulingRun,
        *,
        version_name: str = "Generated Timetable",
        version_number: int = 1,
        scope_kind: str | None = None,
        scope_id: str | None = None,
        baseline_version_id: str | None = None,
    ) -> SchedulingExecutionResult:

        if scheduling_run.status not in (
            SchedulingRunStatus.PENDING,
            SchedulingRunStatus.RUNNING,
        ):
            raise ValueError(
                "Scheduling run must be PENDING or RUNNING "
                "before execution."
            )

        self._mark_running(scheduling_run)

        try:
            hints = compute_hints_for_scope(
                term=scheduling_run.term,
                scope_kind=scope_kind,
                scope_id=scope_id,
                baseline_version_id=baseline_version_id,
            )

            problem = load_scheduling_problem(
                term=scheduling_run.term,
                hint_assignments=hints,
            )

            # PRE-FLIGHT: deterministic domain diagnostics run
            # BEFORE the solver. They are conservative and cheap
            # (seconds vs. minutes) and only fire when the input
            # provably cannot be scheduled — e.g. a teacher is the
            # only eligible one and requires more periods than
            # exist, or a group needs more periods than the week
            # contains. When they fire, INFEASIBLE is guaranteed,
            # so we return immediately with the diagnostics and
            # the required input. The solver is not run.
            from apps.scheduling.engine.solver.infeasibility_diagnostics import (
                analyze_infeasibility as _preflight,
            )
            from apps.scheduling.engine.solver.result import (
                SolverResult as _SolverResult,
            )
            from apps.scheduling.engine.domain.enums import (
                SolverStatus as _SolverStatus,
            )

            _report = _preflight(problem)
            if not _report.is_empty:
                _diag_msg = (
                    'Pre-flight check found conflicts that would '
                    'make the timetable infeasible.\n\n'
                    + _report.format_message()
                )
                result = _SolverResult(
                    status=_SolverStatus.INFEASIBLE,
                    error_message=_diag_msg,
                )
            else:
                # Scoped runs are anchored: the out-of-scope layout is
                # pinned by hint_assignments, so the solver only has the
                # scope's own groups to re-arrange. 180s is ample and
                # saves ~12 minutes per run. Master runs (no hints) keep
                # the default 900s.
                _original_time_limit = None
                if hints:
                    _solver_obj = getattr(self.scheduler, "solver", None)
                    if _solver_obj is not None and hasattr(
                        _solver_obj, "time_limit_seconds"
                    ):
                        _original_time_limit = _solver_obj.time_limit_seconds
                        import os as _os_tl
                        _scoped_tl = float(_os_tl.environ.get("ST_SCOPED_TIME_LIMIT", "180"))
                        _solver_obj.time_limit_seconds = _scoped_tl
                        import sys as _s_tl
                        print(
                            "[TIME_LIMIT] scoped run: "
                            f"{_original_time_limit}s -> {_scoped_tl}s",
                            file=_s_tl.stderr,
                        )
                try:
                    result = self.scheduler.generate(problem)
                finally:
                    if _original_time_limit is not None:
                        _solver_obj.time_limit_seconds = _original_time_limit


            scheduling_run.solver_result = result

            if not result.is_successful:
                message = self._failure_message(result)

                self._mark_failed(
                    scheduling_run,
                    message,
                    solver_result=result,
                )

                return SchedulingExecutionResult(
                    scheduling_run=scheduling_run,
                    solver_result=result,
                    persistence_result=None,
                )

            with transaction.atomic():
                persistence_result = self.persistence.persist(
                    scheduling_run=scheduling_run,
                    solver_result=result,
                    version_name=version_name,
                    version_number=version_number,
                )

                if persistence_result is not None:
                    scheduling_run.persistence_result = persistence_result

                # Post-solve Form 4 practicals (guarded; never blocks generation)
                try:
                    from apps.scheduling.engine.application.form4_practicals import (
                        insert_form4_practicals,
                    )
                    insert_form4_practicals(scheduling_run)
                except Exception as _e_prac:
                    import sys as _sys_prac
                    print(
                        f"[PRACTICALS] wrapper error: {_e_prac}",
                        file=_sys_prac.stderr,
                    )

            return SchedulingExecutionResult(
                scheduling_run=scheduling_run,
                solver_result=result,
                persistence_result=getattr(
                    scheduling_run,
                    "persistence_result",
                    None,
                ),
            )

        except ValueError as exc:
            self._mark_failed(scheduling_run, str(exc))
            raise

        except Exception as exc:
            self._mark_failed(
                scheduling_run,
                str(exc),
            )
            raise

    # ------------------------------------------------------------------
    # RUN STATE
    # ------------------------------------------------------------------

    @staticmethod
    def _mark_running(
        scheduling_run: SchedulingRun,
    ) -> None:
        scheduling_run.status = SchedulingRunStatus.RUNNING
        scheduling_run.started_at = timezone.now()
        scheduling_run.error_message = ""

        scheduling_run.save(
            update_fields=[
                "status",
                "started_at",
                "error_message",
                "updated_at",
            ]
        )

    @staticmethod
    def _mark_completed(
        scheduling_run: SchedulingRun,
        result,
        entry_count: int,
    ) -> None:
        scheduling_run.status = SchedulingRunStatus.COMPLETED
        scheduling_run.completed_at = timezone.now()
        scheduling_run.error_message = ""

        solver_status = getattr(
            result,
            "status",
            None,
        )

        if solver_status is not None:
            scheduling_run.solver_status = (
                solver_status.value
                if hasattr(solver_status, "value")
                else str(solver_status)
            )

        objective_value = getattr(
            result,
            "objective_value",
            None,
        )

        if objective_value is None:
            statistics = getattr(
                result,
                "statistics",
                None,
            )

            if statistics is not None:
                objective_value = getattr(
                    statistics,
                    "objective_value",
                    None,
                )

        if objective_value is not None:
            scheduling_run.objective_value = objective_value

        statistics = getattr(
            result,
            "statistics",
            None,
        )

        if statistics is None:
            statistics = {}

        elif hasattr(statistics, "__dict__"):
            statistics = dict(vars(statistics))

        else:
            try:
                statistics = dict(statistics)
            except (TypeError, ValueError):
                statistics = {}

        statistics["generated_entries"] = entry_count

        scheduling_run.statistics = statistics

        scheduling_run.save(
            update_fields=[
                "status",
                "completed_at",
                "error_message",
                "solver_status",
                "objective_value",
                "statistics",
                "updated_at",
            ]
        )

    @staticmethod
    def _mark_failed(
        scheduling_run: SchedulingRun,
        message: str,
        solver_result=None,
    ) -> None:
        scheduling_run.status = SchedulingRunStatus.FAILED
        scheduling_run.completed_at = timezone.now()
        scheduling_run.error_message = str(message)

        if solver_result is not None:
            solver_status = getattr(solver_result, "status", None)

            if solver_status is not None:
                status_value = (
                    solver_status.value
                    if hasattr(solver_status, "value")
                    else str(solver_status)
                )

                scheduling_run.solver_status = (
                    status_value
                    if status_value in {
                        "FEASIBLE",
                        "OPTIMAL",
                        "INFEASIBLE",
                        "UNKNOWN",
                    }
                    else "ERROR"
                )

        scheduling_run.save(
            update_fields=[
                "status",
                "completed_at",
                "error_message",
                "solver_status",
                "updated_at",
            ]
        )


    # ------------------------------------------------------------------
    # ERROR REPORTING
    # ------------------------------------------------------------------

    @staticmethod
    def _failure_message(result) -> str:

        message = getattr(
            result,
            "message",
            None,
        )

        if message:
            return str(message)

        message = getattr(
            result,
            "error_message",
            None,
        )

        if message:
            return str(message)

        status = getattr(
            result,
            "status",
            None,
        )

        if status is not None:
            status = (
                status.value
                if hasattr(status, "value")
                else str(status)
            )

            return (
                "Scheduling solver finished with status "
                f"{status}."
            )

        return "Scheduling solver finished unsuccessfully."


