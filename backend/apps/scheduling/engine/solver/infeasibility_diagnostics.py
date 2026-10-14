from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from apps.scheduling.engine.application.grade10_parallel_blocks import is_senior_school_instructional_group
from apps.scheduling.engine.application.grade10_parallel_blocks import (
    get_grade10_parallel_block_for_subject,
    is_grade10_instructional_group,
)
from apps.scheduling.engine.domain.enums import DayOfWeek
from apps.scheduling.engine.domain.problem import SchedulingProblem


@dataclass(frozen=True, slots=True)
class InfeasibilityDiagnostic:
    code: str
    rule: str
    message: str
    required_input: str
    details: dict[str, Any]

    def format_message(self) -> str:
        return (
            f"[{self.code}] {self.rule}\n"
            f"Problem: {self.message}\n"
            f"Required input: {self.required_input}\n"
        )


@dataclass(frozen=True, slots=True)
class InfeasibilityReport:
    diagnostics: tuple[InfeasibilityDiagnostic, ...]

    @property
    def is_empty(self) -> bool:
        return not self.diagnostics

    def format_message(self) -> str:
        if not self.diagnostics:
            return "TIMETABLE GENERATION FAILED: No deterministic infeasibility diagnostic was identified."

        lines = [
            "TIMETABLE GENERATION FAILED",
            "",
            "The solver reported the timetable as infeasible.",
            "The following input/rule conflicts were identified:",
            "",
        ]

        for index, diagnostic in enumerate(self.diagnostics, start=1):
            lines.append(f"{index}. {diagnostic.rule}")
            lines.append(f"   Problem: {diagnostic.message}")
            lines.append(
                f"   Required input: {diagnostic.required_input}"
            )

            if diagnostic.details:
                lines.append("   Details:")
                for key, value in diagnostic.details.items():
                    lines.append(f"      {key}: {value}")

            lines.append("")

        return "\n".join(lines)


def _grade_level_from_group_code(code: object) -> str:
    """Extract the leading grade-level prefix from a group code.

    '10E' -> '10'  |  '11W' -> '11'  |  '4E' -> '4'  |  '9W' -> '9'.

    Used to deduplicate BLOCK-typed lesson requirements that are
    synchronized across the streams of one grade level (e.g. 10E and
    10W for the COMP/BUS/MUSD elective blocks). A teacher teaching
    the same BLOCK subject to both streams is one physical teaching
    event; without dedup, capacity diagnostics over-count by a factor
    of the stream count.
    """
    c = str(code or "").strip().upper()
    i = 0
    while i < len(c) and c[i].isdigit():
        i += 1
    return c[:i] or c


def _teacher_name(
    problem: SchedulingProblem,
    teacher_id: UUID,
) -> str:
    teacher = problem.teacher_by_id.get(teacher_id)

    if teacher is None:
        return str(teacher_id)

    code = getattr(teacher, "code", None)
    name = getattr(teacher, "name", None)

    if code and name:
        return f"{code} ({name})"

    return code or name or str(teacher_id)


def _group_name(
    problem: SchedulingProblem,
    group_id: UUID,
) -> str:
    group = problem.instructional_group_by_id.get(group_id)

    if group is None:
        return str(group_id)

    code = getattr(group, "code", None)
    name = getattr(group, "name", None)

    if code and name:
        return f"{code} ({name})"

    return code or name or str(group_id)


def _room_name(
    problem: SchedulingProblem,
    room_id: UUID,
) -> str:
    room = problem.room_by_id.get(room_id)

    if room is None:
        return str(room_id)

    code = getattr(room, "code", None)
    name = getattr(room, "name", None)

    if code and name:
        return f"{code} ({name})"

    return code or name or str(room_id)


def _requirement_name(
    problem: SchedulingProblem,
    requirement,
) -> str:
    subject_code = getattr(requirement, "subject_code", None)

    group_name = _group_name(
        problem,
        requirement.instructional_group_id,
    )

    if subject_code:
        return f"{subject_code} / {group_name}"

    return (
        f"Requirement {requirement.id} / "
        f"{group_name} / "
        f"subject {requirement.subject_id}"
    )


def _active_teacher_ids(
    problem: SchedulingProblem,
) -> set[UUID]:
    return {
        teacher.id
        for teacher in problem.teachers
        if teacher.is_active
    }


def _active_group_ids(
    problem: SchedulingProblem,
) -> set[UUID]:
    return {
        group.id
        for group in problem.instructional_groups
        if group.is_active
    }


def _active_room_ids(
    problem: SchedulingProblem,
) -> set[UUID]:
    return {
        room.id
        for room in problem.rooms
        if room.is_active
    }


def _eligible_teachers_by_requirement(
    problem: SchedulingProblem,
) -> dict[UUID, tuple[UUID, ...]]:
    active_teacher_ids = _active_teacher_ids(problem)

    mapping: dict[UUID, list[UUID]] = {}

    for assignment in problem.teacher_assignments:
        if not assignment.is_active:
            continue

        if assignment.teacher_id not in active_teacher_ids:
            continue

        mapping.setdefault(
            assignment.lesson_requirement_id,
            [],
        ).append(assignment.teacher_id)

    return {
        requirement_id: tuple(dict.fromkeys(teacher_ids))
        for requirement_id, teacher_ids in mapping.items()
    }


def _teacher_unavailable_slots(
    problem: SchedulingProblem,
) -> set[tuple[UUID, object, UUID]]:
    return {
        (
            availability.teacher_id,
            availability.day,
            availability.period_id,
        )
        for availability in problem.teacher_availability
        if availability.is_active
        and not availability.is_available
    }


def _room_unavailable_slots(
    problem: SchedulingProblem,
) -> set[tuple[UUID, object, UUID]]:
    return {
        (
            availability.room_id,
            availability.day,
            availability.period_id,
        )
        for availability in problem.room_availability
        if availability.is_active
        and not availability.is_available
    }


def _teacher_free_afternoons(
    problem: SchedulingProblem,
) -> dict[UUID, object]:
    mapping: dict[UUID, object] = {}

    for assignment in problem.teacher_free_afternoons:
        if not assignment.is_active:
            continue

        mapping[assignment.teacher_id] = assignment.day

    return mapping


def _usable_rooms_for_slot(
    problem: SchedulingProblem,
    *,
    day,
    period_id: UUID,
    room_ids: set[UUID],
    room_unavailable: set[tuple[UUID, object, UUID]],
) -> set[UUID]:
    return {
        room_id
        for room_id in room_ids
        if (
            room_id,
            day,
            period_id,
        ) not in room_unavailable
    }


def _is_schedulable_teaching_slot(
    problem: SchedulingProblem,
    *,
    day: DayOfWeek,
    period_id: UUID,
) -> bool:
    period = problem.period_by_id.get(period_id)

    if (
        period is None
        or not period.is_active
        or not period.is_teaching_period
    ):
        return False

    return not (
        day == DayOfWeek.MONDAY
        and period.number == 1
    )


def _teacher_can_use_slot(
    problem: SchedulingProblem,
    *,
    teacher_id: UUID,
    day,
    period_id: UUID,
    teacher_unavailable: set[tuple[UUID, object, UUID]],
    teacher_free_afternoons: dict[UUID, object],
) -> bool:
    if not _is_schedulable_teaching_slot(
        problem,
        day=day,
        period_id=period_id,
    ):
        return False

    if (
        teacher_id,
        day,
        period_id,
    ) in teacher_unavailable:
        return False

    free_afternoon = teacher_free_afternoons.get(teacher_id)

    if free_afternoon is not None:
        period = problem.period_by_id.get(period_id)

        if (
            period is not None
            and period.is_active
            and period.is_teaching_period
            and period.part_of_day.value == "AFTERNOON"
            and day == free_afternoon
        ):
            return False

    return True


def _candidate_slot_keys(
    problem: SchedulingProblem,
    *,
    eligible_teacher_ids: tuple[UUID, ...],
    room_ids: set[UUID],
    teacher_unavailable: set[tuple[UUID, object, UUID]],
    teacher_free_afternoons: dict[UUID, object],
    room_unavailable: set[tuple[UUID, object, UUID]],
) -> set[tuple[object, UUID]]:
    candidates: set[tuple[object, UUID]] = set()

    for teacher_id in eligible_teacher_ids:
        for slot in problem.slots:
            if not _is_schedulable_teaching_slot(
                problem,
                day=slot.day,
                period_id=slot.period_id,
            ):
                continue

            if not _teacher_can_use_slot(
                problem,
                teacher_id=teacher_id,
                day=slot.day,
                period_id=slot.period_id,
                teacher_unavailable=teacher_unavailable,
                teacher_free_afternoons=teacher_free_afternoons,
            ):
                continue

            usable_rooms = _usable_rooms_for_slot(
                problem,
                day=slot.day,
                period_id=slot.period_id,
                room_ids=room_ids,
                room_unavailable=room_unavailable,
            )

            if not usable_rooms:
                continue

            candidates.add(
                (
                    slot.day,
                    slot.period_id,
                )
            )

    return candidates


def _diagnose_basic_configuration(
    problem: SchedulingProblem,
) -> list[InfeasibilityDiagnostic]:
    diagnostics: list[InfeasibilityDiagnostic] = []

    active_teaching_periods = problem.teaching_periods

    active_rooms = [
        room
        for room in problem.rooms
        if room.is_active
    ]

    active_groups = [
        group
        for group in problem.instructional_groups
        if group.is_active
    ]

    if not active_teaching_periods:
        diagnostics.append(
            InfeasibilityDiagnostic(
                code="NO_ACTIVE_TEACHING_PERIODS",
                rule="Active teaching periods",
                message=(
                    "The timetable has no active teaching periods "
                    "available to the solver."
                ),
                required_input=(
                    "Create or activate at least one timetable period "
                    "with is_teaching_period=True."
                ),
                details={
                    "active_teaching_periods": 0,
                },
            )
        )

    if not active_rooms:
        diagnostics.append(
            InfeasibilityDiagnostic(
                code="NO_ACTIVE_ROOMS",
                rule="Room availability",
                message=(
                    "There are no active rooms available for generated "
                    "lessons."
                ),
                required_input=(
                    "Create or activate at least one room that can host "
                    "the required lessons."
                ),
                details={
                    "active_rooms": 0,
                },
            )
        )

    if not active_groups:
        diagnostics.append(
            InfeasibilityDiagnostic(
                code="NO_ACTIVE_INSTRUCTIONAL_GROUPS",
                rule="Active instructional groups",
                message=(
                    "There are no active instructional groups available "
                    "to receive lessons."
                ),
                required_input=(
                    "Create or activate at least one instructional group "
                    "for the timetable."
                ),
                details={
                    "active_instructional_groups": 0,
                },
            )
        )

    return diagnostics


def _diagnose_requirements(
    problem: SchedulingProblem,
) -> list[InfeasibilityDiagnostic]:
    diagnostics: list[InfeasibilityDiagnostic] = []

    active_teacher_ids = _active_teacher_ids(problem)
    active_group_ids = _active_group_ids(problem)
    active_room_ids = _active_room_ids(problem)

    eligible_by_requirement = _eligible_teachers_by_requirement(problem)
    teacher_unavailable = _teacher_unavailable_slots(problem)
    room_unavailable = _room_unavailable_slots(problem)
    teacher_free_afternoons = _teacher_free_afternoons(problem)

    for requirement in problem.lesson_requirements:
        if not requirement.is_active:
            continue

        requirement_label = _requirement_name(
            problem,
            requirement,
        )

        if requirement.instructional_group_id not in active_group_ids:
            diagnostics.append(
                InfeasibilityDiagnostic(
                    code="INACTIVE_INSTRUCTIONAL_GROUP",
                    rule="Active instructional group",
                    message=(
                        f"{requirement_label} belongs to an inactive "
                        "instructional group."
                    ),
                    required_input=(
                        "Activate the instructional group or "
                        "deactivate/remove the lesson requirement."
                    ),
                    details={
                        "lesson_requirement_id": str(requirement.id),
                        "instructional_group_id": str(
                            requirement.instructional_group_id
                        ),
                    },
                )
            )
            continue

        eligible_teacher_ids = tuple(
            teacher_id
            for teacher_id in eligible_by_requirement.get(
                requirement.id,
                (),
            )
            if teacher_id in active_teacher_ids
        )

        if not eligible_teacher_ids:
            continue

        if not active_room_ids:
            continue

        candidates = _candidate_slot_keys(
            problem,
            eligible_teacher_ids=eligible_teacher_ids,
            room_ids=active_room_ids,
            teacher_unavailable=teacher_unavailable,
            teacher_free_afternoons=teacher_free_afternoons,
            room_unavailable=room_unavailable,
        )

        available_slots = len(candidates)
        required_slots = requirement.periods_per_week

        if available_slots < required_slots:
            teacher_labels = ", ".join(
                _teacher_name(problem, teacher_id)
                for teacher_id in eligible_teacher_ids
            )

            diagnostics.append(
                InfeasibilityDiagnostic(
                    code="LESSON_SLOT_CAPACITY",
                    rule="Weekly lesson requirement capacity",
                    message=(
                        f"{requirement_label} requires "
                        f"{required_slots} lesson(s) per week, but only "
                        f"{available_slots} valid timetable slot(s) "
                        "remain after applying teacher, free-afternoon "
                        "and room-availability rules."
                    ),
                    required_input=(
                        "Increase the number of valid available slots, "
                        "add another eligible active teacher, make the "
                        "teacher available in more periods, change the "
                        "teacher's free-afternoon assignment, make more "
                        "rooms available, or reduce the weekly lesson "
                        "requirement."
                    ),
                    details={
                        "lesson_requirement_id": str(requirement.id),
                        "required_periods": required_slots,
                        "available_slots": available_slots,
                        "eligible_teachers": teacher_labels,
                        "active_rooms": len(active_room_ids),
                    },
                )
            )

    return diagnostics


def _effective_requirement_counts_by_group(
    problem: SchedulingProblem,
) -> dict[UUID, int]:
    """
    Calculate effective weekly instructional demand by instructional group.

    Senior-school BLOCK requirements belonging to a canonical senior-school
    elective block share one timetable allocation. The canonical block
    allocation is therefore counted once per instructional group.

    Grade 10 parallel elective blocks retain their existing subject-code/block
    detection and max-per-block treatment. This remains independent of the
    requirement_type field because legacy/synthetic Grade 10 fixtures may not
    explicitly set that field.

    STANDALONE and PRACTICAL requirements remain independent and retain their
    own periods_per_week values.
    """
    from apps.scheduling.engine.solver.model import (
        _senior_school_block_weekly_shared_slots,
        senior_school_block_code_for_subject,
    )

    requirements_by_group: dict[UUID, int] = {}
    senior_school_block_counts: dict[tuple[UUID, str], int] = {}
    grade10_parallel_block_counts: dict[tuple[UUID, str], int] = {}

    for requirement in problem.lesson_requirements:
        if not requirement.is_active:
            continue

        group_id = requirement.instructional_group_id
        group = problem.instructional_group_by_id.get(group_id)

        requirement_type = str(
            getattr(
                requirement,
                "requirement_type",
                "STANDALONE",
            )
            or "STANDALONE"
        ).upper()

        subject_code = requirement.subject_code

        # Senior-school blocks are canonical BLOCK requirements. Practical
        # requirements such as CS practicals must remain independent.
        senior_block_code = None
        if requirement_type == "BLOCK" and is_senior_school_instructional_group(group):
            senior_block_code = senior_school_block_code_for_subject(
                subject_code
            )

        if (
            requirement_type == "BLOCK"
            and senior_block_code is not None
        ):
            key = (group_id, senior_block_code)
            shared_slots = _senior_school_block_weekly_shared_slots(
                senior_block_code
            )
            senior_school_block_counts[key] = max(
                senior_school_block_counts.get(key, 0),
                shared_slots,
            )
            continue

        # Grade 10 parallel blocks are identified by their instructional
        # group and subject code, preserving the established behavior for
        # fixtures whose requirement_type defaults to STANDALONE.
        grade10_block = (
            get_grade10_parallel_block_for_subject(subject_code)
            if is_grade10_instructional_group(group)
            else None
        )

        if grade10_block is not None:
            key = (group_id, grade10_block.code)
            grade10_parallel_block_counts[key] = max(
                grade10_parallel_block_counts.get(key, 0),
                requirement.periods_per_week,
            )
            continue

        requirements_by_group[group_id] = (
            requirements_by_group.get(group_id, 0)
            + requirement.periods_per_week
        )

    for (group_id, _block_code), periods_per_week in (
        senior_school_block_counts.items()
    ):
        requirements_by_group[group_id] = (
            requirements_by_group.get(group_id, 0)
            + periods_per_week
        )

    for (group_id, _block_code), periods_per_week in (
        grade10_parallel_block_counts.items()
    ):
        requirements_by_group[group_id] = (
            requirements_by_group.get(group_id, 0)
            + periods_per_week
        )

    return requirements_by_group


def _group_teaching_slot_count(
    problem: SchedulingProblem,
) -> int:
    count = 0

    for slot in problem.slots:
        if not _is_schedulable_teaching_slot(
            problem,
            day=slot.day,
            period_id=slot.period_id,
        ):
            continue

        count += 1

    return count


def _diagnose_group_capacity(
    problem: SchedulingProblem,
) -> list[InfeasibilityDiagnostic]:
    diagnostics: list[InfeasibilityDiagnostic] = []

    teaching_slot_count = _group_teaching_slot_count(problem)

    if teaching_slot_count == 0:
        return diagnostics

    requirements_by_group = _effective_requirement_counts_by_group(
        problem
    )

    for group_id, required_periods in requirements_by_group.items():
        if required_periods <= teaching_slot_count:
            continue

        group_name = _group_name(
            problem,
            group_id,
        )

        diagnostics.append(
            InfeasibilityDiagnostic(
                code="INSTRUCTIONAL_GROUP_CAPACITY",
                rule="Instructional-group clash capacity",
                message=(
                    f"{group_name} requires {required_periods} total "
                    f"lesson periods per week, but only "
                    f"{teaching_slot_count} timetable teaching slots "
                    "exist for that group."
                ),
                required_input=(
                    "Increase the number of active teaching periods "
                    "or reduce the total weekly lesson requirements "
                    "for this instructional group."
                ),
                details={
                    "instructional_group_id": str(group_id),
                    "required_periods": required_periods,
                    "available_group_slots": teaching_slot_count,
                },
            )
        )

    return diagnostics


def _diagnose_single_teacher_capacity(
    problem: SchedulingProblem,
) -> list[InfeasibilityDiagnostic]:
    diagnostics: list[InfeasibilityDiagnostic] = []

    active_teacher_ids = _active_teacher_ids(problem)

    eligible_by_requirement = _eligible_teachers_by_requirement(problem)
    teacher_unavailable = _teacher_unavailable_slots(problem)
    teacher_free_afternoons = _teacher_free_afternoons(problem)

    # Deduplicate BLOCK-typed LRs within the same grade level.
    #
    # A BLOCK-typed LR's subject is synchronized across the streams of
    # the same grade (e.g. 10E and 10W for COMP/BUS/MUSD). One teacher
    # teaching BUS to both 10E and 10W represents ONE physical teaching
    # event (5 slots) — not two. Without this dedup the diagnostic
    # over-counts by the number of streams and reports a false
    # TEACHER_CAPACITY finding on every infeasible model.
    block_required_by_teacher: dict[UUID, dict[tuple, int]] = defaultdict(dict)
    nonblock_required_by_teacher: dict[UUID, int] = defaultdict(int)

    for requirement in problem.lesson_requirements:
        if not requirement.is_active:
            continue

        eligible = tuple(
            teacher_id
            for teacher_id in eligible_by_requirement.get(
                requirement.id,
                (),
            )
            if teacher_id in active_teacher_ids
        )

        if len(eligible) != 1:
            continue

        teacher_id = eligible[0]
        periods = int(getattr(requirement, "periods_per_week", 0) or 0)

        rtype = str(
            getattr(requirement, "requirement_type", "") or ""
        ).strip().upper()

        if rtype == "BLOCK":
            subject_code = str(
                getattr(requirement, "subject_code", "") or ""
            ).strip().upper()

            group_code = ""
            group_id = getattr(requirement, "instructional_group_id", None)
            if group_id is not None:
                group = next(
                    (
                        g
                        for g in problem.instructional_groups
                        if getattr(g, "id", None) == group_id
                    ),
                    None,
                )
                if group is not None:
                    group_code = str(getattr(group, "code", "") or "")

            grade = _grade_level_from_group_code(group_code)
            key = (subject_code, grade)

            # Same key within the same teacher = same synchronized
            # physical event; keep the max (they should all be equal
            # when the block registry is consistent, but max is safe).
            prev = block_required_by_teacher[teacher_id].get(key, 0)
            if periods > prev:
                block_required_by_teacher[teacher_id][key] = periods
        else:
            nonblock_required_by_teacher[teacher_id] += periods

    required_by_teacher: dict[UUID, int] = {}
    for teacher_id in (
        set(block_required_by_teacher)
        | set(nonblock_required_by_teacher)
    ):
        required_by_teacher[teacher_id] = (
            sum(block_required_by_teacher.get(teacher_id, {}).values())
            + nonblock_required_by_teacher.get(teacher_id, 0)
        )

    for teacher_id, required_periods in required_by_teacher.items():
        available_slots = 0

        for slot in problem.slots:
            if _teacher_can_use_slot(
                problem,
                teacher_id=teacher_id,
                day=slot.day,
                period_id=slot.period_id,
                teacher_unavailable=teacher_unavailable,
                teacher_free_afternoons=teacher_free_afternoons,
            ):
                available_slots += 1

        if required_periods <= available_slots:
            continue

        diagnostics.append(
            InfeasibilityDiagnostic(
                code="TEACHER_CAPACITY",
                rule="Teacher weekly capacity",
                message=(
                    f"{_teacher_name(problem, teacher_id)} is the only "
                    f"eligible teacher for {required_periods} required "
                    f"lesson period(s), but only {available_slots} "
                    "valid teaching slots are available to that teacher."
                ),
                required_input=(
                    "Assign another active eligible teacher, make more "
                    "periods available to the teacher, change the "
                    "teacher's free-afternoon assignment, or reduce "
                    "the teacher's mandatory weekly lesson load."
                ),
                details={
                    "teacher_id": str(teacher_id),
                    "teacher": _teacher_name(problem, teacher_id),
                    "required_periods": required_periods,
                    "available_slots": available_slots,
                },
            )
        )

    return diagnostics


def _diagnose_room_capacity(
    problem: SchedulingProblem,
) -> list[InfeasibilityDiagnostic]:
    diagnostics: list[InfeasibilityDiagnostic] = []

    active_room_ids = _active_room_ids(problem)

    if not active_room_ids:
        return diagnostics

    room_unavailable = _room_unavailable_slots(problem)

    total_required_periods = sum(
        requirement.periods_per_week
        for requirement in problem.lesson_requirements
        if requirement.is_active
    )

    total_room_slot_capacity = 0

    for slot in problem.slots:
        if not _is_schedulable_teaching_slot(
            problem,
            day=slot.day,
            period_id=slot.period_id,
        ):
            continue

        total_room_slot_capacity += len(
            _usable_rooms_for_slot(
                problem,
                day=slot.day,
                period_id=slot.period_id,
                room_ids=active_room_ids,
                room_unavailable=room_unavailable,
            )
        )

    if total_required_periods <= total_room_slot_capacity:
        return diagnostics

    diagnostics.append(
        InfeasibilityDiagnostic(
            code="ROOM_CAPACITY",
            rule="Room-slot capacity",
            message=(
                f"The timetable requires {total_required_periods} "
                f"lesson placements, but the active rooms provide only "
                f"{total_room_slot_capacity} usable room-slot placements."
            ),
            required_input=(
                "Activate additional rooms, make currently unavailable "
                "rooms available in more periods, increase the number "
                "of teaching periods, or reduce weekly lesson demand."
            ),
            details={
                "required_lesson_placements": total_required_periods,
                "available_room_slots": total_room_slot_capacity,
                "active_rooms": len(active_room_ids),
                "rooms": ", ".join(
                    _room_name(problem, room_id)
                    for room_id in sorted(
                        active_room_ids,
                        key=str,
                    )
                ),
            },
        )
    )

    return diagnostics


def analyze_infeasibility(
    problem: SchedulingProblem,
) -> InfeasibilityReport:
    """
    Analyze a SchedulingProblem after CP-SAT reports INFEASIBLE.

    Diagnostics are conservative: a finding is emitted only where
    the supplied scheduling data proves that the relevant capacity
    or eligibility rule cannot be satisfied.
    """

    diagnostics: list[InfeasibilityDiagnostic] = []

    diagnostics.extend(
        _diagnose_basic_configuration(problem)
    )

    diagnostics.extend(
        _diagnose_requirements(problem)
    )

    diagnostics.extend(
        _diagnose_group_capacity(problem)
    )

    diagnostics.extend(
        _diagnose_single_teacher_capacity(problem)
    )

    diagnostics.extend(
        _diagnose_room_capacity(problem)
    )

    unique: list[InfeasibilityDiagnostic] = []
    seen: set[tuple[str, str]] = set()

    for diagnostic in diagnostics:
        key = (
            diagnostic.code,
            diagnostic.message,
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(diagnostic)

    return InfeasibilityReport(
        diagnostics=tuple(unique),
    )
