from __future__ import annotations

from dataclasses import dataclass

from apps.scheduling.engine.application.scheduler import (
    SchedulingService,
    create_default_scheduler,
)
from apps.scheduling.engine.application.timetable_persistence import (
    PersistenceResult,
    TimetablePersistenceService,
)
from apps.scheduling.engine.domain.enums import SolverStatus
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.infrastructure.django_loader import (
    load_scheduling_problem,
)
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
)


@dataclass(frozen=True, slots=True)
class SchedulingExecutionResult:
    """
    Result of one complete timetable-generation execution.

    Represents the application-level outcome after the scheduling
    problem has been loaded, solved and, when successful, persisted.
    """

    scheduling_run: SchedulingRun
    solver_result: SolverResult
    persistence_result: PersistenceResult | None = None


class SchedulingApplicationService:
    """
    Application-level orchestration for timetable generation.

    Coordinates:

        Django database
            ↓
        SchedulingProblem
            ↓
        SchedulingService
            ↓
        SolverResult
            ↓
        TimetablePersistenceService

    This class owns the use-case workflow but does not implement
    scheduling constraints or solver construction itself.
    """

    def __init__(
        self,
        *,
        scheduler: SchedulingService | None = None,
        persistence: TimetablePersistenceService | None = None,
    ) -> None:
        self.scheduler = scheduler or create_default_scheduler()
        self.persistence = (
            persistence or TimetablePersistenceService()
        )

    def execute(
        self,
        *,
        scheduling_run: SchedulingRun,
        version_name: str,
        version_number: int,
    ) -> SchedulingExecutionResult:
        """
        Execute one complete timetable-generation workflow.

        The scheduling run must be PENDING or RUNNING.

        Successful FEASIBLE or OPTIMAL solver results are persisted
        as a timetable version.

        Unsuccessful solver results are returned without creating
        a timetable version.
        """

        self._validate_run(scheduling_run)

        if scheduling_run.status == SchedulingRunStatus.PENDING:
            self._mark_running(scheduling_run)

        problem = self._load_problem(
            scheduling_run=scheduling_run,
        )

        solver_result = self.scheduler.generate(problem)

        if solver_result.status not in {
            SolverStatus.FEASIBLE,
            SolverStatus.OPTIMAL,
        }:
            self._mark_failed_solver_run(
                scheduling_run=scheduling_run,
                solver_result=solver_result,
            )

            return SchedulingExecutionResult(
                scheduling_run=scheduling_run,
                solver_result=solver_result,
                persistence_result=None,
            )

        persistence_result = self.persistence.persist(
            scheduling_run=scheduling_run,
            solver_result=solver_result,
            version_name=version_name,
            version_number=version_number,
        )

        return SchedulingExecutionResult(
            scheduling_run=scheduling_run,
            solver_result=solver_result,
            persistence_result=persistence_result,
        )

    # ------------------------------------------------------------------
    # Problem loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_problem(
        *,
        scheduling_run: SchedulingRun,
    ) -> SchedulingProblem:
        """
        Load all scheduling inputs for the run's term.

        Django model access remains confined to the infrastructure
        loader. The application layer receives a domain problem.
        """

        return load_scheduling_problem(
            term=scheduling_run.term,
        )

    # ------------------------------------------------------------------
    # Scheduling-run lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_run(
        scheduling_run: SchedulingRun,
    ) -> None:
        """Ensure the run is in an executable state."""

        if scheduling_run.status not in {
            SchedulingRunStatus.PENDING,
            SchedulingRunStatus.RUNNING,
        }:
            raise ValueError(
                "Scheduling run must be PENDING or RUNNING before "
                "execution."
            )

    @staticmethod
    def _mark_running(
        scheduling_run: SchedulingRun,
    ) -> None:
        """Move a pending scheduling run into the running state."""

        from django.utils import timezone

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
    def _mark_failed_solver_run(
        *,
        scheduling_run: SchedulingRun,
        solver_result: SolverResult,
    ) -> None:
        """
        Record an unsuccessful solver outcome.

        No timetable version is created for unsuccessful solver
        results.
        """

        from django.utils import timezone

        scheduling_run.status = SchedulingRunStatus.FAILED
        scheduling_run.completed_at = timezone.now()
        scheduling_run.solver_status = (
            SchedulingApplicationService._django_solver_status(
                solver_result.status,
            )
        )

        scheduling_run.statistics = {
            "wall_time_seconds": (
                solver_result.statistics.wall_time_seconds
            ),
            "branches": solver_result.statistics.branches,
            "conflicts": solver_result.statistics.conflicts,
            "entries_created": 0,
        }

        scheduling_run.error_message = (
            "Scheduling solver finished with status "
            f"{solver_result.status.value}."
        )

        scheduling_run.save(
            update_fields=[
                "status",
                "completed_at",
                "solver_status",
                "statistics",
                "error_message",
                "updated_at",
            ]
        )

    @staticmethod
    def _django_solver_status(
        status: SolverStatus,
    ) -> str:
        """Map domain solver status to Django model status."""

        from apps.scheduling.models import (
            SolverStatus as DjangoSolverStatus,
        )

        mapping = {
            SolverStatus.FEASIBLE: DjangoSolverStatus.FEASIBLE,
            SolverStatus.OPTIMAL: DjangoSolverStatus.OPTIMAL,
            SolverStatus.INFEASIBLE: DjangoSolverStatus.INFEASIBLE,
            SolverStatus.UNKNOWN: DjangoSolverStatus.UNKNOWN,
            SolverStatus.MODEL_INVALID: DjangoSolverStatus.ERROR,
            SolverStatus.TIME_LIMIT: DjangoSolverStatus.UNKNOWN,
            SolverStatus.FAILED: DjangoSolverStatus.ERROR,
            SolverStatus.NOT_STARTED: DjangoSolverStatus.NOT_RUN,
        }

        return mapping[status]