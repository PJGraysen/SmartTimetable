from __future__ import annotations

from datetime import time
from uuid import uuid4

from apps.scheduling.engine.domain.entities import (
    LessonRequirementEntity,
    PeriodEntity,
    RoomAvailabilityEntity,
    RoomEntity,
    SchedulingAssignment,
    TeacherAvailabilityEntity,
    TeacherEntity,
    TeacherFreeAfternoonEntity,
    TeachingGroupEntity,
)
from apps.scheduling.engine.domain.enums import (
    DayOfWeek,
    PartOfDay,
    ValidationCategory,
    ValidationSeverity,
)
from apps.scheduling.engine.domain.problem import SchedulingProblem
from apps.scheduling.engine.validation.rules import (
    validate_duplicate_entries,
    validate_invalid_assignments,
    validate_lesson_requirements,
    validate_room_availability,
    validate_room_clashes,
    validate_teacher_availability,
    validate_teacher_clashes,
    validate_teacher_free_afternoons,
    validate_teaching_group_clashes,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def make_period(
    *,
    number: int = 1,
    part_of_day: PartOfDay = PartOfDay.MORNING,
) -> PeriodEntity:
    return PeriodEntity(
        id=uuid4(),
        number=number,
        name=f"Period {number}",
        start_time=time(8, 0),
        end_time=time(8, 40),
        part_of_day=part_of_day,
        is_teaching_period=True,
    )


def make_teacher() -> TeacherEntity:
    return TeacherEntity(
        id=uuid4(),
        name="Teacher One",
        code="T001",
    )


def make_group() -> TeachingGroupEntity:
    return TeachingGroupEntity(
        id=uuid4(),
        name="Form 1A",
        code="F1A",
    )


def make_room() -> RoomEntity:
    return RoomEntity(
        id=uuid4(),
        name="Room 1",
        code="R1",
        capacity=50,
    )


def make_requirement(
    *,
    group_id,
    periods_per_week: int = 1,
) -> LessonRequirementEntity:
    return LessonRequirementEntity(
        id=uuid4(),
        teaching_group_id=group_id,
        subject_id=uuid4(),
        periods_per_week=periods_per_week,
    )


def make_assignment(
    *,
    requirement,
    teacher,
    group,
    period,
    day: DayOfWeek = DayOfWeek.MONDAY,
    room=None,
) -> SchedulingAssignment:
    return SchedulingAssignment(
        lesson_requirement_id=requirement.id,
        teacher_id=teacher.id,
        teaching_group_id=group.id,
        period_id=period.id,
        day=day,
        room_id=room.id if room else None,
    )


def make_problem(
    *,
    periods,
    teachers,
    groups,
    rooms,
    requirements,
    teacher_assignments=(),
    teacher_availability=(),
    teacher_free_afternoons=None,
    room_availability=(),
    slots=(),
) -> SchedulingProblem:
    """
    Build a valid SchedulingProblem fixture.

    The domain requires every active teacher to have exactly one
    active free-afternoon assignment. Most validation-rule tests are
    not specifically testing that domain invariant, so when the test
    does not explicitly provide free-afternoon assignments, give each
    active teacher a valid default assignment.

    Passing an explicit value, including an empty tuple, preserves
    the caller's intent.
    """

    if teacher_free_afternoons is None:
        teacher_free_afternoons = tuple(
            TeacherFreeAfternoonEntity(
                id=uuid4(),
                teacher_id=teacher.id,
                day=DayOfWeek.FRIDAY,
            )
            for teacher in teachers
            if teacher.is_active
        )

    return SchedulingProblem.from_iterables(
        periods=periods,
        teachers=teachers,
        teaching_groups=groups,
        rooms=rooms,
        lesson_requirements=requirements,
        teacher_assignments=teacher_assignments,
        teacher_availability=teacher_availability,
        teacher_free_afternoons=teacher_free_afternoons,
        room_availability=room_availability,
        slots=slots,
    )


# ---------------------------------------------------------------------------
# Teacher clashes
# ---------------------------------------------------------------------------


def test_teacher_clash_is_detected():
    teacher = make_teacher()
    group_one = make_group()
    group_two = make_group()
    room_one = make_room()
    room_two = make_room()
    period = make_period()

    requirement_one = make_requirement(group_id=group_one.id)
    requirement_two = make_requirement(group_id=group_two.id)

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher,
        group=group_one,
        period=period,
        room=room_one,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher,
        group=group_two,
        period=period,
        room=room_two,
    )

    findings = validate_teacher_clashes(
        (assignment_one, assignment_two)
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert findings[0].category == ValidationCategory.TEACHER_CLASH.value
    assert findings[0].teacher_id == str(teacher.id)


def test_different_teachers_do_not_clash():
    teacher_one = make_teacher()
    teacher_two = make_teacher()
    group_one = make_group()
    group_two = make_group()
    period = make_period()

    requirement_one = make_requirement(group_id=group_one.id)
    requirement_two = make_requirement(group_id=group_two.id)

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher_one,
        group=group_one,
        period=period,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher_two,
        group=group_two,
        period=period,
    )

    findings = validate_teacher_clashes(
        (assignment_one, assignment_two)
    )

    assert findings == ()


# ---------------------------------------------------------------------------
# Teaching-group clashes
# ---------------------------------------------------------------------------


def test_teaching_group_clash_is_detected():
    teacher_one = make_teacher()
    teacher_two = make_teacher()
    group = make_group()
    period = make_period()

    requirement_one = make_requirement(group_id=group.id)
    requirement_two = make_requirement(group_id=group.id)

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher_one,
        group=group,
        period=period,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher_two,
        group=group,
        period=period,
    )

    findings = validate_teaching_group_clashes(
        (assignment_one, assignment_two)
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert findings[0].category == ValidationCategory.GROUP_CLASH.value
    assert findings[0].teaching_group_id == str(group.id)


# ---------------------------------------------------------------------------
# Room clashes
# ---------------------------------------------------------------------------


def test_room_clash_is_detected():
    teacher_one = make_teacher()
    teacher_two = make_teacher()
    group_one = make_group()
    group_two = make_group()
    room = make_room()
    period = make_period()

    requirement_one = make_requirement(group_id=group_one.id)
    requirement_two = make_requirement(group_id=group_two.id)

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher_one,
        group=group_one,
        period=period,
        room=room,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher_two,
        group=group_two,
        period=period,
        room=room,
    )

    findings = validate_room_clashes(
        (assignment_one, assignment_two)
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert findings[0].category == ValidationCategory.ROOM_CLASH.value
    assert findings[0].room_id == str(room.id)


def test_assignments_without_rooms_do_not_create_room_clashes():
    teacher_one = make_teacher()
    teacher_two = make_teacher()
    group_one = make_group()
    group_two = make_group()
    period = make_period()

    requirement_one = make_requirement(group_id=group_one.id)
    requirement_two = make_requirement(group_id=group_two.id)

    assignment_one = make_assignment(
        requirement=requirement_one,
        teacher=teacher_one,
        group=group_one,
        period=period,
    )

    assignment_two = make_assignment(
        requirement=requirement_two,
        teacher=teacher_two,
        group=group_two,
        period=period,
    )

    findings = validate_room_clashes(
        (assignment_one, assignment_two)
    )

    assert findings == ()


# ---------------------------------------------------------------------------
# Teacher availability
# ---------------------------------------------------------------------------


def test_teacher_unavailability_is_detected():
    teacher = make_teacher()
    group = make_group()
    period = make_period()
    requirement = make_requirement(group_id=group.id)

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
        day=DayOfWeek.MONDAY,
    )

    availability = TeacherAvailabilityEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
        period_id=period.id,
        is_available=False,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
        teacher_availability=(availability,),
    )

    findings = validate_teacher_availability(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.TEACHER_AVAILABILITY.value
    )


# ---------------------------------------------------------------------------
# Teacher free afternoon
# ---------------------------------------------------------------------------


def test_teacher_free_afternoon_violation_is_detected():
    teacher = make_teacher()
    group = make_group()
    afternoon_period = make_period(
        number=6,
        part_of_day=PartOfDay.AFTERNOON,
    )
    requirement = make_requirement(group_id=group.id)

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=afternoon_period,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(afternoon_period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    findings = validate_teacher_free_afternoons(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.TEACHER_FREE_AFTERNOON.value
    )
    assert findings[0].teacher_id == str(teacher.id)


def test_teacher_free_afternoon_does_not_block_morning():
    teacher = make_teacher()
    group = make_group()
    morning_period = make_period(
        number=1,
        part_of_day=PartOfDay.MORNING,
    )
    requirement = make_requirement(group_id=group.id)

    free_afternoon = TeacherFreeAfternoonEntity(
        id=uuid4(),
        teacher_id=teacher.id,
        day=DayOfWeek.MONDAY,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=morning_period,
        day=DayOfWeek.MONDAY,
    )

    problem = make_problem(
        periods=(morning_period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
        teacher_free_afternoons=(free_afternoon,),
    )

    findings = validate_teacher_free_afternoons(
        problem,
        (assignment,),
    )

    assert findings == ()


# ---------------------------------------------------------------------------
# Room availability
# ---------------------------------------------------------------------------


def test_room_unavailability_is_detected():
    teacher = make_teacher()
    group = make_group()
    room = make_room()
    period = make_period()
    requirement = make_requirement(group_id=group.id)

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
        room=room,
    )

    availability = RoomAvailabilityEntity(
        id=uuid4(),
        room_id=room.id,
        day=DayOfWeek.MONDAY,
        period_id=period.id,
        is_available=False,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(room,),
        requirements=(requirement,),
        room_availability=(availability,),
    )

    findings = validate_room_availability(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.ROOM_AVAILABILITY.value
    )


# ---------------------------------------------------------------------------
# Duplicate entries
# ---------------------------------------------------------------------------


def test_duplicate_timetable_entries_are_detected():
    teacher = make_teacher()
    group = make_group()
    room = make_room()
    period = make_period()
    requirement = make_requirement(group_id=group.id)

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
        room=room,
    )

    findings = validate_duplicate_entries(
        (assignment, assignment)
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.DUPLICATE_ENTRY.value
    )


# ---------------------------------------------------------------------------
# Invalid assignments
# ---------------------------------------------------------------------------


def test_assignment_referencing_unknown_teacher_is_detected():
    teacher = make_teacher()
    unknown_teacher = make_teacher()
    group = make_group()
    period = make_period()
    requirement = make_requirement(group_id=group.id)

    assignment = make_assignment(
        requirement=requirement,
        teacher=unknown_teacher,
        group=group,
        period=period,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
    )

    findings = validate_invalid_assignments(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.INVALID_ASSIGNMENT.value
    )


def test_assignment_referencing_unknown_period_is_detected():
    teacher = make_teacher()
    group = make_group()
    known_period = make_period(number=1)
    unknown_period = make_period(number=2)
    requirement = make_requirement(group_id=group.id)

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=unknown_period,
    )

    problem = make_problem(
        periods=(known_period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
    )

    findings = validate_invalid_assignments(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.INVALID_ASSIGNMENT.value
    )


# ---------------------------------------------------------------------------
# Lesson requirements
# ---------------------------------------------------------------------------


def test_lesson_requirement_shortfall_is_detected():
    teacher = make_teacher()
    group = make_group()
    period = make_period()
    requirement = make_requirement(
        group_id=group.id,
        periods_per_week=2,
    )

    assignment = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period,
    )

    problem = make_problem(
        periods=(period,),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
    )

    findings = validate_lesson_requirements(
        problem,
        (assignment,),
    )

    assert len(findings) == 1
    assert findings[0].severity == ValidationSeverity.ERROR.value
    assert (
        findings[0].category
        == ValidationCategory.LESSON_REQUIREMENT.value
    )


def test_lesson_requirement_is_satisfied():
    teacher = make_teacher()
    group = make_group()
    period_one = make_period(number=1)
    period_two = make_period(number=2)

    requirement = make_requirement(
        group_id=group.id,
        periods_per_week=2,
    )

    assignment_one = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period_one,
    )

    assignment_two = make_assignment(
        requirement=requirement,
        teacher=teacher,
        group=group,
        period=period_two,
        day=DayOfWeek.TUESDAY,
    )

    problem = make_problem(
        periods=(period_one, period_two),
        teachers=(teacher,),
        groups=(group,),
        rooms=(),
        requirements=(requirement,),
    )

    findings = validate_lesson_requirements(
        problem,
        (assignment_one, assignment_two),
    )

    assert findings == ()