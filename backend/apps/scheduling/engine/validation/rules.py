from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from apps.scheduling.engine.domain.entities import SchedulingAssignment
from apps.scheduling.engine.domain.enums import (
    ValidationCategory,
    ValidationSeverity,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.validation.result import ValidationFinding


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _slot_key(
    assignment: SchedulingAssignment,
) -> tuple:
    """
    Return the unique timetable slot identity for an assignment.

    A timetable assignment occupies one teaching-group/teacher/period/day
    combination. Room is intentionally excluded because the same lesson
    assignment remains the same lesson even if room information differs.
    """
    return (
        assignment.lesson_requirement_id,
        assignment.teacher_id,
        assignment.instructional_group_id,
        assignment.period_id,
        assignment.day,
    )


def _assignment_key(
    assignment: SchedulingAssignment,
) -> tuple:
    """
    Return the complete identity of a timetable assignment.

    Used primarily for duplicate-entry detection.
    """
    return (
        assignment.lesson_requirement_id,
        assignment.teacher_id,
        assignment.instructional_group_id,
        assignment.period_id,
        assignment.day,
        assignment.room_id,
    )


def _unique_assignments(
    assignments: Iterable[SchedulingAssignment],
) -> tuple[SchedulingAssignment, ...]:
    """
    Remove exact duplicate timetable entries while preserving order.
    """
    seen: set[tuple] = set()
    unique: list[SchedulingAssignment] = []

    for assignment in assignments:
        key = _assignment_key(assignment)

        if key in seen:
            continue

        seen.add(key)
        unique.append(assignment)

    return tuple(unique)


def _finding(
    *,
    severity: ValidationSeverity,
    category: ValidationCategory,
    message: str,
    assignment: SchedulingAssignment | None = None,
    **details,
) -> ValidationFinding:
    """
    Construct a ValidationFinding consistently.
    """
    return ValidationFinding(
        severity=severity.value,
        category=category.value,
        message=message,
        details=details,
        teacher_id=(
            str(assignment.teacher_id)
            if assignment is not None
            else None
        ),
        instructional_group_id=(
            str(assignment.instructional_group_id)
            if assignment is not None
            else None
        ),
        period_id=(
            str(assignment.period_id)
            if assignment is not None
            else None
        ),
        day=(
            assignment.day.value
            if assignment is not None
            else None
        ),
        room_id=(
            str(assignment.room_id)
            if assignment is not None and assignment.room_id is not None
            else None
        ),
    )


# ---------------------------------------------------------------------------
# Teacher clashes
# ---------------------------------------------------------------------------


def validate_teacher_clashes(
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect teachers assigned to more than one lesson in the same
    day/period.
    """
    findings: list[ValidationFinding] = []

    assignments_by_slot: dict[
        tuple,
        list[SchedulingAssignment],
    ] = defaultdict(list)

    for assignment in _unique_assignments(assignments):
        key = (
            assignment.teacher_id,
            assignment.day,
            assignment.period_id,
        )
        assignments_by_slot[key].append(assignment)

    for (
        teacher_id,
        day,
        period_id,
    ), grouped in assignments_by_slot.items():

        if len(grouped) <= 1:
            continue

        first = grouped[0]

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.TEACHER_CLASH,
                message=(
                    "Teacher is assigned to multiple lessons "
                    "during the same day and period."
                ),
                assignment=first,
                teacher_id=str(teacher_id),
                day=day.value,
                period_id=str(period_id),
                conflicting_assignment_ids=[
                    str(item.lesson_requirement_id)
                    for item in grouped
                ],
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Teaching-group clashes
# ---------------------------------------------------------------------------


def validate_instructional_group_clashes(
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect teaching groups assigned to more than one lesson in the same
    day/period.
    """
    findings: list[ValidationFinding] = []

    assignments_by_slot: dict[
        tuple,
        list[SchedulingAssignment],
    ] = defaultdict(list)

    for assignment in _unique_assignments(assignments):
        key = (
            assignment.instructional_group_id,
            assignment.day,
            assignment.period_id,
        )
        assignments_by_slot[key].append(assignment)

    for (
        group_id,
        day,
        period_id,
    ), grouped in assignments_by_slot.items():

        if len(grouped) <= 1:
            continue

        first = grouped[0]

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.GROUP_CLASH,
                message=(
                    "Teaching group is assigned to multiple lessons "
                    "during the same day and period."
                ),
                assignment=first,
                instructional_group_id=str(group_id),
                day=day.value,
                period_id=str(period_id),
                conflicting_assignment_ids=[
                    str(item.lesson_requirement_id)
                    for item in grouped
                ],
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Room clashes
# ---------------------------------------------------------------------------


def validate_room_clashes(
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect rooms assigned to more than one lesson in the same day/period.

    Assignments without a room are ignored.
    """
    findings: list[ValidationFinding] = []

    assignments_by_slot: dict[
        tuple,
        list[SchedulingAssignment],
    ] = defaultdict(list)

    for assignment in _unique_assignments(assignments):
        if assignment.room_id is None:
            continue

        key = (
            assignment.room_id,
            assignment.day,
            assignment.period_id,
        )
        assignments_by_slot[key].append(assignment)

    for (
        room_id,
        day,
        period_id,
    ), grouped in assignments_by_slot.items():

        if len(grouped) <= 1:
            continue

        first = grouped[0]

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.ROOM_CLASH,
                message=(
                    "Room is assigned to multiple lessons "
                    "during the same day and period."
                ),
                assignment=first,
                room_id=str(room_id),
                day=day.value,
                period_id=str(period_id),
                conflicting_assignment_ids=[
                    str(item.lesson_requirement_id)
                    for item in grouped
                ],
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Teacher availability
# ---------------------------------------------------------------------------


def validate_teacher_availability(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect assignments made during periods when the assigned teacher
    is explicitly unavailable.
    """
    findings: list[ValidationFinding] = []

    availability_map = {
        (
            item.teacher_id,
            item.day,
            item.period_id,
        ): item
        for item in problem.teacher_availability
        if item.is_active
    }

    for assignment in _unique_assignments(assignments):
        availability = availability_map.get(
            (
                assignment.teacher_id,
                assignment.day,
                assignment.period_id,
            )
        )

        if availability is None:
            continue

        if availability.is_available:
            continue

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.TEACHER_AVAILABILITY,
                message=(
                    "Teacher is assigned to a period during which "
                    "the teacher is unavailable."
                ),
                assignment=assignment,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Teacher free afternoon
# ---------------------------------------------------------------------------


def validate_teacher_free_afternoons(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Enforce the hard teacher free-afternoon constraint.

    Every active teacher has exactly one designated free afternoon.
    A teacher must have no afternoon teaching assignment on that day.
    """
    findings: list[ValidationFinding] = []

    free_afternoons = {
        (
            item.teacher_id,
            item.day,
        )
        for item in problem.teacher_free_afternoons
        if item.is_active
    }

    afternoon_period_ids = {
        period.id
        for period in problem.periods
        if period.is_active
        and period.is_teaching_period
        and period.part_of_day.value == "AFTERNOON"
    }

    for assignment in _unique_assignments(assignments):

        if assignment.period_id not in afternoon_period_ids:
            continue

        if (
            assignment.teacher_id,
            assignment.day,
        ) not in free_afternoons:
            continue

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.TEACHER_FREE_AFTERNOON,
                message=(
                    "Teacher is assigned to an afternoon teaching "
                    "period on the teacher's designated free afternoon."
                ),
                assignment=assignment,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Room availability
# ---------------------------------------------------------------------------


def validate_room_availability(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect assignments made to rooms during periods when those rooms
    are explicitly unavailable.
    """
    findings: list[ValidationFinding] = []

    availability_map = {
        (
            item.room_id,
            item.day,
            item.period_id,
        ): item
        for item in problem.room_availability
        if item.is_active
    }

    for assignment in _unique_assignments(assignments):

        if assignment.room_id is None:
            continue

        availability = availability_map.get(
            (
                assignment.room_id,
                assignment.day,
                assignment.period_id,
            )
        )

        if availability is None:
            continue

        if availability.is_available:
            continue

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.ROOM_AVAILABILITY,
                message=(
                    "Room is assigned to a period during which "
                    "the room is unavailable."
                ),
                assignment=assignment,
            )
        )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Duplicate timetable entries
# ---------------------------------------------------------------------------


def validate_duplicate_entries(
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect exact duplicate timetable entries.

    Two entries are duplicates when all assignment identity fields match.
    """
    findings: list[ValidationFinding] = []

    seen: dict[tuple, SchedulingAssignment] = {}

    for assignment in assignments:
        key = _assignment_key(assignment)

        if key not in seen:
            seen[key] = assignment
            continue

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.DUPLICATE_ENTRY,
                message=(
                    "Duplicate timetable entry detected."
                ),
                assignment=assignment,
                duplicate_of_requirement_id=str(
                    seen[key].lesson_requirement_id
                ),
            )
        )

        # One finding per duplicated identity is sufficient.
        # Do not repeatedly report the same duplicate.
        seen[key] = assignment

    return tuple(findings)


# ---------------------------------------------------------------------------
# Invalid assignments
# ---------------------------------------------------------------------------


def validate_invalid_assignments(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Detect assignments that reference entities not present in the
    scheduling problem.
    """
    findings: list[ValidationFinding] = []

    teacher_ids = {
        teacher.id
        for teacher in problem.teachers
        if teacher.is_active
    }

    group_ids = {
        group.id
        for group in problem.instructional_groups
        if group.is_active
    }

    period_ids = {
        period.id
        for period in problem.periods
        if period.is_active
    }

    room_ids = {
        room.id
        for room in problem.rooms
        if room.is_active
    }

    requirement_ids = {
        requirement.id
        for requirement in problem.lesson_requirements
        if requirement.is_active
    }

    for assignment in _unique_assignments(assignments):

        # teacher_id=None is a valid pending teacher allocation.
        if (
            assignment.teacher_id is not None
            and assignment.teacher_id not in teacher_ids
        ):
            findings.append(
                _finding(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVALID_ASSIGNMENT,
                    message=(
                        "Assignment references an unknown or inactive teacher."
                    ),
                    assignment=assignment,
                    invalid_teacher_id=str(assignment.teacher_id),
                )
            )

        if assignment.instructional_group_id not in group_ids:
            findings.append(
                _finding(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVALID_ASSIGNMENT,
                    message=(
                        "Assignment references an unknown or inactive "
                        "teaching group."
                    ),
                    assignment=assignment,
                    invalid_instructional_group_id=str(
                        assignment.instructional_group_id
                    ),
                )
            )

        if assignment.period_id not in period_ids:
            findings.append(
                _finding(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVALID_ASSIGNMENT,
                    message=(
                        "Assignment references an unknown or inactive period."
                    ),
                    assignment=assignment,
                    invalid_period_id=str(assignment.period_id),
                )
            )

        if assignment.room_id is not None and assignment.room_id not in room_ids:
            findings.append(
                _finding(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVALID_ASSIGNMENT,
                    message=(
                        "Assignment references an unknown or inactive room."
                    ),
                    assignment=assignment,
                    invalid_room_id=str(assignment.room_id),
                )
            )

        if assignment.lesson_requirement_id not in requirement_ids:
            findings.append(
                _finding(
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.INVALID_ASSIGNMENT,
                    message=(
                        "Assignment references an unknown or inactive "
                        "lesson requirement."
                    ),
                    assignment=assignment,
                    invalid_lesson_requirement_id=str(
                        assignment.lesson_requirement_id
                    ),
                )
            )

    return tuple(findings)


# ---------------------------------------------------------------------------
# Lesson requirements
# ---------------------------------------------------------------------------


def validate_lesson_requirements(
    problem: SchedulingProblem,
    assignments: Iterable[SchedulingAssignment],
) -> tuple[ValidationFinding, ...]:
    """
    Validate that every active lesson requirement receives exactly the
    required number of weekly teaching periods.

    IMPORTANT:
    Duplicate timetable entries must NOT count as additional lessons.

    For example, if a requirement needs two periods per week and the
    same timetable assignment appears twice, only one unique lesson is
    counted. This allows the duplicate-entry validator and the lesson
    requirement validator to report both problems independently.
    """
    findings: list[ValidationFinding] = []

    # This is the important correction:
    #
    # We first remove exact duplicate timetable entries before counting
    # assignments against weekly lesson requirements.
    unique_assignments = _unique_assignments(assignments)

    assignment_counts: dict = defaultdict(int)
    first_assignment: dict = {}

    for assignment in unique_assignments:
        requirement_id = assignment.lesson_requirement_id

        assignment_counts[requirement_id] += 1

        if requirement_id not in first_assignment:
            first_assignment[requirement_id] = assignment

    for requirement in problem.lesson_requirements:

        if not requirement.is_active:
            continue

        actual_count = assignment_counts.get(
            requirement.id,
            0,
        )

        expected_count = requirement.periods_per_week

        if actual_count == expected_count:
            continue

        assignment = first_assignment.get(requirement.id)

        findings.append(
            _finding(
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.LESSON_REQUIREMENT,
                message=(
                    "Lesson requirement is not satisfied: "
                    f"expected {expected_count} periods per week, "
                    f"but found {actual_count} unique scheduled periods."
                ),
                assignment=assignment,
                lesson_requirement_id=str(requirement.id),
                expected_periods_per_week=expected_count,
                actual_periods_per_week=actual_count,
            )
        )

    return tuple(findings)
