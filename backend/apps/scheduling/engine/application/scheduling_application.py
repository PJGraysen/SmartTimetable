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


def load_scheduling_problem(*, term):
    """
    Compatibility boundary for the application-layer scheduling loader.

    Kept as a module-level function so the application service remains
    independently patchable by the application-layer test contract.
    """
    loader = DjangoSchedulingLoader()
    return loader.load_problem(term=term)


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
            problem = load_scheduling_problem(
                term=scheduling_run.term,
            )

            result = self.scheduler.generate(problem)

            scheduling_run.solver_result = result

            if not result.is_successful:
                message = self._failure_message(result)

                self._mark_failed(
                    scheduling_run,
                    message,
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

            return SchedulingExecutionResult(
                scheduling_run=scheduling_run,
                solver_result=result,
                persistence_result=getattr(
                    scheduling_run,
                    "persistence_result",
                    None,
                ),
            )

        except ValueError:
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
    ) -> None:
        scheduling_run.status = SchedulingRunStatus.FAILED
        scheduling_run.completed_at = timezone.now()
        scheduling_run.error_message = str(message)

        scheduling_run.save(
            update_fields=[
                "status",
                "completed_at",
                "error_message",
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


