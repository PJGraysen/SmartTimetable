from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.enums import SolverStatus as DomainSolverStatus
from apps.scheduling.engine.solver.result import SolverResult
from apps.scheduling.models import (
    SchedulingRun,
    SchedulingRunStatus,
    SolverStatus as DjangoSolverStatus,
    TimetableEntry,
    TimetableVersion,
)


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    """Result of persisting a generated timetable."""

    timetable_version: TimetableVersion
    scheduling_run: SchedulingRun
    entries_created: int


class TimetablePersistenceService:
    """
    Persist a successful solver result as a timetable version.

    This service is responsible for the application/persistence boundary.

    Solver construction and execution remain independent of Django
    persistence. The service guarantees that timetable version creation,
    timetable entry creation, and scheduling-run completion occur as one
    atomic operation.
    """

    @transaction.atomic
    def persist(
        self,
        *,
        scheduling_run: SchedulingRun,
        solver_result: SolverResult,
        version_name: str,
        version_number: int,
    ) -> PersistenceResult:
        """
        Persist a successful solver result.

        The complete persistence operation is atomic. If validation,
        timetable-version creation, timetable-entry creation, or
        scheduling-run update fails, the entire transaction is rolled back.
        """

        self._validate_solver_result(solver_result)

        self._validate_scheduling_run(scheduling_run)

        self._validate_version_details(
            version_name=version_name,
            version_number=version_number,
        )

        assignments = tuple(solver_result.assignments)

        self._validate_assignments(assignments)

        # --------------------------------------------------------------
        # Create the timetable version.
        # --------------------------------------------------------------

        timetable_version = TimetableVersion.objects.create(
            term=scheduling_run.term,
            name=version_name.strip(),
            version_number=version_number,
            is_published=False,
            is_active=True,
        )

        # --------------------------------------------------------------
        # Convert solver assignments into timetable entries.
        # --------------------------------------------------------------

        entries = self._build_entries(
            timetable_version=timetable_version,
            assignments=assignments,
        )

        if entries:
            TimetableEntry.objects.bulk_create(entries)

        # --------------------------------------------------------------
        # Complete the scheduling run and explicitly associate it with
        # the timetable version that was just created.
        # --------------------------------------------------------------

        self._complete_scheduling_run(
            scheduling_run=scheduling_run,
            timetable_version=timetable_version,
            solver_result=solver_result,
            entries_created=len(entries),
        )

        return PersistenceResult(
            timetable_version=timetable_version,
            scheduling_run=scheduling_run,
            entries_created=len(entries),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_solver_result(
        solver_result: SolverResult,
    ) -> None:
        """Validate that the solver produced a persistable result."""

        if not solver_result.is_successful:
            raise ValueError(
                "Only FEASIBLE or OPTIMAL solver results can be persisted."
            )

        if solver_result.status not in {
            DomainSolverStatus.FEASIBLE,
            DomainSolverStatus.OPTIMAL,
        }:
            raise ValueError(
                "Unsupported solver status for persistence: "
                f"{solver_result.status!r}"
            )

    @staticmethod
    def _validate_scheduling_run(
        scheduling_run: SchedulingRun,
    ) -> None:
        """Validate the scheduling-run lifecycle state."""

        if scheduling_run.status not in {
            SchedulingRunStatus.PENDING,
            SchedulingRunStatus.RUNNING,
        }:
            raise ValueError(
                "Scheduling run must be PENDING or RUNNING before "
                "timetable persistence."
            )

    @staticmethod
    def _validate_version_details(
        *,
        version_name: str,
        version_number: int,
    ) -> None:
        """Validate timetable-version metadata."""

        if not version_name.strip():
            raise ValueError(
                "Timetable version name cannot be empty."
            )

        if version_number < 1:
            raise ValueError(
                "Timetable version number must be greater than zero."
            )

    @staticmethod
    def _validate_assignments(
        assignments: Iterable[SchedulingAssignment],
    ) -> None:
        """
        Validate all solver assignments before database insertion.

        This deliberately validates foreign-key references at the
        application boundary instead of allowing PostgreSQL to discover
        invalid references during transaction teardown.

        The validation also ensures that a solver assignment is internally
        consistent with its lesson requirement and related entities.
        """

        assignments = tuple(assignments)

        if not assignments:
            return

        lesson_requirement_ids = {
            assignment.lesson_requirement_id
            for assignment in assignments
        }

        teacher_ids = {
            assignment.teacher_id
            for assignment in assignments
        }

        teaching_group_ids = {
            assignment.teaching_group_id
            for assignment in assignments
        }

        period_ids = {
            assignment.period_id
            for assignment in assignments
        }

        from apps.academics.models import LessonRequirement, TeachingGroup
        from apps.scheduling.models import Period
        from apps.users.models import Teacher

        # --------------------------------------------------------------
        # Validate lesson requirements.
        # --------------------------------------------------------------

        existing_requirement_ids = set(
            LessonRequirement.objects.filter(
                id__in=lesson_requirement_ids,
            ).values_list("id", flat=True)
        )

        missing_requirements = (
            lesson_requirement_ids - existing_requirement_ids
        )

        if missing_requirements:
            raise ValueError(
                "Solver assignment references unknown lesson "
                "requirement(s): "
                f"{sorted(str(value) for value in missing_requirements)}"
            )

        # --------------------------------------------------------------
        # Validate teachers.
        # --------------------------------------------------------------

        existing_teacher_ids = set(
            Teacher.objects.filter(
                id__in=teacher_ids,
            ).values_list("id", flat=True)
        )

        missing_teachers = teacher_ids - existing_teacher_ids

        if missing_teachers:
            raise ValueError(
                "Solver assignment references unknown teacher(s): "
                f"{sorted(str(value) for value in missing_teachers)}"
            )

        # --------------------------------------------------------------
        # Validate teaching groups.
        # --------------------------------------------------------------

        existing_group_ids = set(
            TeachingGroup.objects.filter(
                id__in=teaching_group_ids,
            ).values_list("id", flat=True)
        )

        missing_groups = teaching_group_ids - existing_group_ids

        if missing_groups:
            raise ValueError(
                "Solver assignment references unknown teaching "
                "group(s): "
                f"{sorted(str(value) for value in missing_groups)}"
            )

        # --------------------------------------------------------------
        # Validate periods.
        # --------------------------------------------------------------

        existing_period_ids = set(
            Period.objects.filter(
                id__in=period_ids,
            ).values_list("id", flat=True)
        )

        missing_periods = period_ids - existing_period_ids

        if missing_periods:
            raise ValueError(
                "Solver assignment references unknown period(s): "
                f"{sorted(str(value) for value in missing_periods)}"
            )

        # --------------------------------------------------------------
        # Validate lesson-requirement relationships.
        # --------------------------------------------------------------

        requirements = {
            requirement.id: requirement
            for requirement in LessonRequirement.objects.filter(
                id__in=lesson_requirement_ids,
            )
        }

        for assignment in assignments:
            requirement = requirements[assignment.lesson_requirement_id]

            if (
                assignment.teaching_group_id
                != requirement.teaching_group_id
            ):
                raise ValueError(
                    "Solver assignment teaching group does not match "
                    "the lesson requirement teaching group for lesson "
                    f"requirement {requirement.id}."
                )

    # ------------------------------------------------------------------
    # Timetable entry construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_entries(
        *,
        timetable_version: TimetableVersion,
        assignments: Iterable[SchedulingAssignment],
    ) -> list[TimetableEntry]:
        """
        Convert domain scheduling assignments into Django timetable
        entries.
        """

        return [
            TimetableEntry(
                timetable_version=timetable_version,
                day=assignment.day.value,
                period_id=assignment.period_id,
                teaching_group_id=assignment.teaching_group_id,
                teacher_id=assignment.teacher_id,
                lesson_requirement_id=assignment.lesson_requirement_id,
                room_id=assignment.room_id,
            )
            for assignment in assignments
        ]

    # ------------------------------------------------------------------
    # Scheduling-run completion
    # ------------------------------------------------------------------

    @staticmethod
    def _complete_scheduling_run(
        *,
        scheduling_run: SchedulingRun,
        timetable_version: TimetableVersion,
        solver_result: SolverResult,
        entries_created: int,
    ) -> None:
        """
        Mark the scheduling run as successfully completed.

        The scheduling run is explicitly linked to the timetable version
        produced by this execution.
        """

        objective_value: Decimal | None = None

        if solver_result.statistics.objective_value is not None:
            objective_value = Decimal(
                str(solver_result.statistics.objective_value)
            )

        # --------------------------------------------------------------
        # Update scheduling-run lifecycle information.
        # --------------------------------------------------------------

        scheduling_run.status = SchedulingRunStatus.COMPLETED

        scheduling_run.timetable_version = timetable_version

        scheduling_run.solver_status = (
            TimetablePersistenceService._solver_status(
                solver_result.status
            )
        )

        scheduling_run.completed_at = timezone.now()

        scheduling_run.objective_value = objective_value

        scheduling_run.statistics = {
            "wall_time_seconds": (
                solver_result.statistics.wall_time_seconds
            ),
            "branches": solver_result.statistics.branches,
            "conflicts": solver_result.statistics.conflicts,
            "entries_created": entries_created,
        }

        scheduling_run.error_message = ""

        # --------------------------------------------------------------
        # IMPORTANT:
        # timetable_version MUST be included in update_fields.
        #
        # Without this, Django will not write the newly assigned
        # TimetableVersion foreign key to scheduling_run.
        # --------------------------------------------------------------

        scheduling_run.save(
            update_fields=[
                "timetable_version",
                "status",
                "solver_status",
                "completed_at",
                "objective_value",
                "statistics",
                "error_message",
                "updated_at",
            ]
        )

    # ------------------------------------------------------------------
    # Solver-status conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _solver_status(
        status: DomainSolverStatus,
    ) -> str:
        """
        Convert the domain solver status into the Django choice value.
        """

        if status == DomainSolverStatus.FEASIBLE:
            return DjangoSolverStatus.FEASIBLE

        if status == DomainSolverStatus.OPTIMAL:
            return DjangoSolverStatus.OPTIMAL

        raise ValueError(
            "Unsupported solver status for persistence: "
            f"{status!r}"
        )