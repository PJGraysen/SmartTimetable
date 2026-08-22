from __future__ import annotations

from collections.abc import Iterable

from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.problem import SchedulingProblem

from .result import ValidationFinding, ValidationSummary
from .rules import (
    validate_duplicate_entries,
    validate_invalid_assignments,
    validate_lesson_requirements,
    validate_room_availability,
    validate_room_clashes,
    validate_teacher_availability,
    validate_teacher_clashes,
    validate_teacher_free_afternoons,
    validate_instructional_group_clashes,
)


class TimetableValidator:
    """
    Orchestrates all timetable validation rules.

    The validator is deliberately independent of Django and persistence.
    It receives a domain-level SchedulingProblem together with the
    timetable assignments to validate and returns a ValidationSummary.
    """

    def validate(
        self,
        problem: SchedulingProblem,
        assignments: Iterable[SchedulingAssignment],
    ) -> ValidationSummary:
        """
        Validate a timetable against all available validation rules.

        Args:
            problem:
                The scheduling problem containing teachers, groups,
                periods, rooms, requirements, availability and
                free-afternoon constraints.

            assignments:
                The timetable assignments being validated.

        Returns:
            ValidationSummary containing every finding produced by
            the validation rules.
        """
        assignments = tuple(assignments)

        findings: list[ValidationFinding] = []

        # ------------------------------------------------------------------
        # Structural validation
        # ------------------------------------------------------------------

        findings.extend(
            validate_duplicate_entries(assignments)
        )

        findings.extend(
            validate_invalid_assignments(
                problem,
                assignments,
            )
        )

        # ------------------------------------------------------------------
        # Clash validation
        # ------------------------------------------------------------------

        findings.extend(
            validate_teacher_clashes(assignments)
        )

        findings.extend(
            validate_instructional_group_clashes(assignments)
        )

        findings.extend(
            validate_room_clashes(assignments)
        )

        # ------------------------------------------------------------------
        # Availability validation
        # ------------------------------------------------------------------

        findings.extend(
            validate_teacher_availability(
                problem,
                assignments,
            )
        )

        findings.extend(
            validate_room_availability(
                problem,
                assignments,
            )
        )

        # ------------------------------------------------------------------
        # Teacher free-afternoon hard constraint
        # ------------------------------------------------------------------

        findings.extend(
            validate_teacher_free_afternoons(
                problem,
                assignments,
            )
        )

        # ------------------------------------------------------------------
        # Lesson requirement validation
        # ------------------------------------------------------------------

        findings.extend(
            validate_lesson_requirements(
                problem,
                assignments,
            )
        )

        return ValidationSummary(
            findings=tuple(findings),
        )


def validate_timetable(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> ValidationSummary:
    """
    Convenience function for validating a timetable.

    This is the preferred functional API for callers that do not need
    to retain a TimetableValidator instance.
    """
    return TimetableValidator().validate(
        problem,
        assignments,
    )


def validate(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> ValidationSummary:
    """
    Short convenience alias for validate_timetable().
    """
    return validate_timetable(
        problem,
        assignments,
    )
